"""Account repository for database operations on the Account entity."""

from decimal import Decimal
from typing import List

from sqlmodel import Session, select

from budget_app.models import Account, Transaction
from budget_app.schemas import (
    AccountBase,
    AccountType,
    AccountWithBalance,
    SystemEnvelopeType,
    TransactionType,
)


def get_balance_for_account(session: Session, account: Account) -> Decimal:
    """Calculates the current net balance of an account by evaluating all its transactions.

    Excludes reversed transactions and their compensating reversals.
    For Cash accounts:
        Inflows (INCOME, INTEREST_EARNED) increase balance (+).
        Outflows (EXPENSE) decrease balance (-).
    For Debt accounts (Credit Card, Loan):
        Purchases/Charges (EXPENSE, FINANCED, INTEREST_CHARGE) increase debt owed (+).
        Payments/Credits (INCOME) decrease debt owed (-).

    Args:
        session: Active SQLModel database session.
        account: Account instance whose balance is to be calculated.

    Returns:
        The computed balance as Decimal.
    """
    if account.id is None:
        return getattr(account, "_current_balance", Decimal("0.00"))

    stmt = select(Transaction).where(Transaction.payment_method_id == account.id)
    transactions = session.exec(stmt).all()
    if not transactions:
        return getattr(account, "_current_balance", Decimal("0.00"))

    balance = Decimal("0.00")
    for tx in transactions:
        # Exclude reversed transactions and their compensating reversal transactions
        if tx.transaction_type == TransactionType.REVERSAL or (
            tx.note and "[REVERSED]" in tx.note
        ):
            continue

        # Calculate transaction total
        tx_total = Decimal("0.00")
        if tx.transaction_type == TransactionType.FINANCED:
            if tx.splits:
                tx_total = abs(tx.splits[0].amount)
        elif tx.transaction_type in (
            TransactionType.INTEREST_CHARGE,
            TransactionType.INTEREST_EARNED,
        ):
            if tx.splits:
                tx_total = abs(tx.splits[0].amount)
        elif tx.transaction_type == TransactionType.TRANSFER:
            tx_total = Decimal("0.00")
        else:
            is_credit_card = account.account_type == AccountType.CREDIT_CARD
            for split in tx.splits:
                if (
                    is_credit_card
                    and split.envelope is not None
                    and (
                        split.envelope.system_role == SystemEnvelopeType.CREDIT_CARD_PAYMENT
                        or (account.envelope_id is not None and split.envelope_id == account.envelope_id)
                        or split.envelope.name == "Credit Card Payment"
                    )
                ):
                    continue
                tx_total += abs(split.amount)

        if tx_total == Decimal("0.00"):
            continue

        if account.account_type == AccountType.CASH:
            if tx.transaction_type in (
                TransactionType.INCOME,
                TransactionType.INTEREST_EARNED,
            ):
                balance += tx_total
            elif tx.transaction_type == TransactionType.EXPENSE:
                balance -= tx_total
        elif account.account_type in (AccountType.CREDIT_CARD, AccountType.LOAN):
            if tx.transaction_type in (
                TransactionType.EXPENSE,
                TransactionType.FINANCED,
                TransactionType.INTEREST_CHARGE,
            ):
                balance += tx_total
            elif tx.transaction_type == TransactionType.INCOME:
                balance -= tx_total

    return balance


def get_account_by_name(session: Session, account_name: str) -> Account | None:
    """Fetches an account by its unique name, attaching its derived balance.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account to look up.

    Returns:
        The matching Account instance if found, otherwise None.
    """
    stmt = select(Account).where(Account.name == account_name)
    ret_account = session.exec(stmt).one_or_none()
    if ret_account:
        ret_account.current_balance = get_balance_for_account(session, ret_account)
    return ret_account


def get_account_by_id(session: Session, account_id: int) -> Account | None:
    """Fetches an account by its primary key ID, attaching its derived balance.

    Args:
        session: Active SQLModel database session.
        account_id: Integer ID of the account.

    Returns:
        The matching Account instance if found, otherwise None.
    """
    stmt = select(Account).where(Account.id == account_id)
    ret_account = session.exec(stmt).one_or_none()
    if ret_account:
        ret_account.current_balance = get_balance_for_account(session, ret_account)
    return ret_account


def get_accounts(
    session: Session, is_active: bool | None = True
) -> List[Account]:
    """Fetches accounts from database ordered by name, optionally filtered by is_active.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all accounts.
            Defaults to True (active accounts only).

    Returns:
        List of matching Account instances ordered by name.
    """
    stmt = select(Account)
    if is_active is not None:
        stmt = stmt.where(Account.is_active == is_active)
    stmt = stmt.order_by(Account.name)
    accounts = list(session.exec(stmt).all())
    for acc in accounts:
        acc.current_balance = get_balance_for_account(session, acc)
    return accounts


def get_accounts_with_balances(
    session: Session, is_active: bool | None = True
) -> List[AccountWithBalance]:
    """Fetches accounts with dynamically computed balances.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all accounts.
            Defaults to True.

    Returns:
        List of AccountWithBalance instances.
    """
    accounts = get_accounts(session, is_active=is_active)
    result = []
    for acc in accounts:
        bal = get_balance_for_account(session, acc)
        if acc.id is not None:
            result.append(
                AccountWithBalance(
                    id=acc.id,
                    name=acc.name,
                    account_type=acc.account_type,
                    current_balance=bal,
                    total_statement_balance=acc.total_statement_balance,
                    interest_saving_balance=acc.interest_saving_balance,
                    monthly_payment=acc.monthly_payment,
                    due_date=acc.due_date,
                    is_active=acc.is_active,
                    envelope_id=acc.envelope_id,
                )
            )
    return result


def has_non_starting_transactions(session: Session, account_id: int) -> bool:
    """Checks whether an account has any transactions other than Starting Balance transactions.

    Args:
        session: Active SQLModel database session.
        account_id: Integer ID of the account.

    Returns:
        True if at least one transaction exists that is not a 'Starting Balance'
        transaction, False otherwise.
    """
    stmt = (
        select(Transaction.id)
        .where(
            Transaction.payment_method_id == account_id,
            Transaction.merchant != "Starting Balance",
        )
        .limit(1)
    )
    return session.exec(stmt).first() is not None


def create_account(session: Session, new_account: AccountBase) -> Account:
    """Instantiates and stages a new Account entity in the session.

    Args:
        session: Active SQLModel database session.
        new_account: AccountBase schema containing account attributes.

    Returns:
        The staged Account instance (uncommitted).
    """
    account_entry = Account.model_validate(new_account)
    session.add(account_entry)
    return account_entry
