"""Account service for account creation, validation, automated envelope linking, and interest adjustments."""

from datetime import date
from decimal import Decimal
from typing import List

from sqlmodel import Session

from budget_app.models import Account, Transaction
from budget_app.repositories import account_repo, envelope_repo, transaction_repo
from budget_app.schemas import (
    AccountBase,
    AccountType,
    AccountWithBalance,
    EnvelopeBase,
    EnvelopeSplitRequest,
    TransactionRequest,
    TransactionType,
)


def create_account(
    session: Session, acc_info: AccountBase
) -> Account:
    """Creates a new financial account and persists it in the database.

    Validates account name presence, checks for duplicates, enforces account-type specific
    field bounds, auto-links Credit Card accounts to their payment envelope, and automatically
    generates a Starting Balance transaction if an initial balance is provided.

    Args:
        session: Active SQLModel database session.
        acc_info: Account metadata including name, account type, and initial balance.

    Returns:
        The newly created and refreshed Account instance with derived balance.

    Raises:
        ValueError: If name is empty/whitespace, an account with the name already exists,
            or monetary balance/payment amounts are invalid for the given account_type.
    """
    # 1. Validate account name presence
    if not acc_info.name or not acc_info.name.strip():
        raise ValueError("Account name cannot be empty")

    cleaned_name = acc_info.name.strip()
    acc_info.name = cleaned_name

    # 2. Check for duplicate account name
    existing_account = account_repo.get_account_by_name(session, cleaned_name)
    if existing_account:
        raise ValueError(f"Account '{cleaned_name}' already exists")

    # Extract initial/starting balance
    initial_balance = (
        getattr(acc_info, "starting_balance", None)
        or getattr(acc_info, "current_balance", None)
        or Decimal("0.00")
    )

    # 3. Apply account-type specific validation and sanitize irrelevant fields
    if acc_info.account_type == AccountType.CASH:
        if initial_balance < Decimal("0"):
            raise ValueError("Cash account balance cannot be negative")
        # Cash accounts do not have statement balances, interest, or due dates
        acc_info.total_statement_balance = None
        acc_info.interest_saving_balance = None
        acc_info.monthly_payment = None
        acc_info.due_date = None
    elif acc_info.account_type in (AccountType.CREDIT_CARD, AccountType.LOAN):
        if initial_balance < Decimal("0"):
            raise ValueError("Balance cannot be negative")
        if acc_info.monthly_payment is not None and acc_info.monthly_payment < Decimal("0"):
            raise ValueError("Monthly payment cannot be negative")
        if acc_info.total_statement_balance is not None and acc_info.total_statement_balance < Decimal("0"):
            raise ValueError("Statement balance cannot be negative")
        if acc_info.interest_saving_balance is not None and acc_info.interest_saving_balance < Decimal("0"):
            raise ValueError("Interest saving balance cannot be negative")

    # 4. Stage new account
    new_account = account_repo.create_account(session, acc_info)

    # 5. Auto-link Credit Card accounts to 'Credit Card Payment' envelope
    if acc_info.account_type == AccountType.CREDIT_CARD:
        cc_envelope = envelope_repo.get_or_create_envelope(
            session, EnvelopeBase(name="Credit Card Payment")
        )
        new_account.envelope_id = cc_envelope.id

    session.commit()
    session.refresh(new_account)

    # 6. If initial balance > 0, post a Starting Balance transaction
    if initial_balance > Decimal("0.00"):
        if acc_info.account_type == AccountType.CASH:
            envelope_repo.get_or_create_envelope(
                session, EnvelopeBase(name="Unassigned")
            )
            split = EnvelopeSplitRequest(
                amount=initial_balance,
                envelope_name="Unassigned",
            )
            tx_req = TransactionRequest(
                merchant="Starting Balance",
                payment_method_name=cleaned_name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
            )
            transaction_repo.create_transaction(session, tx_req)
        elif acc_info.account_type in (AccountType.CREDIT_CARD, AccountType.LOAN):
            envelope_repo.get_or_create_envelope(
                session, EnvelopeBase(name="Account Adjustment")
            )
            split = EnvelopeSplitRequest(
                amount=initial_balance,
                envelope_name="Account Adjustment",
            )
            tx_req = TransactionRequest(
                merchant="Starting Balance",
                payment_method_name=cleaned_name,
                transaction_type=TransactionType.INTEREST_CHARGE,
                splits=[split],
            )
            transaction_repo.create_transaction(session, tx_req)

        session.commit()
        session.refresh(new_account)

    new_account.current_balance = account_repo.get_balance_for_account(session, new_account)
    return new_account


def add_interest_charge(
    session: Session,
    account_name: str,
    amount: Decimal,
    note: str | None = "Interest Charge",
    logged_date: date | None = None,
) -> Transaction:
    """Logs an interest charge transaction against a debt account.

    Increases the outstanding balance owed on the account without impacting
    active user budgeting envelopes (the split is allocated to 'Account Adjustment').

    Args:
        session: Active SQLModel database session.
        account_name: Name of the Credit Card or Loan account.
        amount: Positive interest charge amount.
        note: Optional description or note.
        logged_date: Date of the charge (defaults to today).

    Returns:
        The created master Transaction instance.

    Raises:
        ValueError: If account does not exist, is not a debt account, or amount <= 0.
    """
    account = account_repo.get_account_by_name(session, account_name)
    if not account:
        raise ValueError(f"Account '{account_name}' does not exist")

    if account.account_type not in (AccountType.CREDIT_CARD, AccountType.LOAN):
        raise ValueError("Interest charges can only be applied to debt accounts (Credit Card or Loan)")

    if amount <= Decimal("0.00"):
        raise ValueError("Interest charge amount must be greater than 0")

    envelope_repo.get_or_create_envelope(session, EnvelopeBase(name="Account Adjustment"))

    split = EnvelopeSplitRequest(
        amount=amount,
        envelope_name="Account Adjustment",
    )
    tx_req = TransactionRequest(
        merchant="Interest Charge",
        logged_date=logged_date or date.today(),
        note=note,
        payment_method_name=account.name,
        transaction_type=TransactionType.INTEREST_CHARGE,
        splits=[split],
    )
    tx = transaction_repo.create_transaction(session, tx_req)
    session.commit()
    session.refresh(tx)
    return tx


def add_interest_earned(
    session: Session,
    account_name: str,
    amount: Decimal,
    note: str | None = "Interest Earned",
    logged_date: date | None = None,
) -> Transaction:
    """Logs an interest earned transaction on a liquid cash or savings account.

    Increases the liquid cash balance on the account and allocates the earned interest
    to the 'Unassigned' envelope, making it immediately available to budget.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the Cash/Savings account.
        amount: Positive interest earned amount.
        note: Optional description or note.
        logged_date: Date of interest receipt (defaults to today).

    Returns:
        The created master Transaction instance.

    Raises:
        ValueError: If account does not exist, is not a Cash account, or amount <= 0.
    """
    account = account_repo.get_account_by_name(session, account_name)
    if not account:
        raise ValueError(f"Account '{account_name}' does not exist")

    if account.account_type != AccountType.CASH:
        raise ValueError("Interest earned can only be applied to Cash/Savings accounts")

    if amount <= Decimal("0.00"):
        raise ValueError("Interest earned amount must be greater than 0")

    envelope_repo.get_or_create_envelope(session, EnvelopeBase(name="Unassigned"))

    split = EnvelopeSplitRequest(
        amount=amount,
        envelope_name="Unassigned",
    )
    tx_req = TransactionRequest(
        merchant="Interest Earned",
        logged_date=logged_date or date.today(),
        note=note,
        payment_method_name=account.name,
        transaction_type=TransactionType.INTEREST_EARNED,
        splits=[split],
    )
    tx = transaction_repo.create_transaction(session, tx_req)
    session.commit()
    session.refresh(tx)
    return tx


def get_account_balance(session: Session, account_name: str) -> Decimal:
    """Fetches the dynamically derived current balance of an account."""
    account = account_repo.get_account_by_name(session, account_name)
    if not account:
        raise ValueError(f"Account '{account_name}' does not exist")
    return account_repo.get_balance_for_account(session, account)


def get_account(session: Session, account_name: str) -> AccountWithBalance | None:
    """Fetches a single account by name with its derived balance."""
    account = account_repo.get_account_by_name(session, account_name)
    if not account or account.id is None:
        return None
    bal = account_repo.get_balance_for_account(session, account)
    return AccountWithBalance(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        current_balance=bal,
        total_statement_balance=account.total_statement_balance,
        interest_saving_balance=account.interest_saving_balance,
        monthly_payment=account.monthly_payment,
        due_date=account.due_date,
        envelope_id=account.envelope_id,
    )


def get_all_accounts(session: Session) -> List[AccountWithBalance]:
    """Fetches all accounts with their dynamically derived balances."""
    return account_repo.get_accounts_with_balances(session)
