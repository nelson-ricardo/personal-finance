"""Account service for account creation, validation, automated envelope linking, and interest adjustments."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlmodel import Session

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories import (
    account_repo,
    category_repo,
    envelope_repo,
    transaction_repo,
)
from budget_app.schemas import (
    AccountBase,
    AccountCreate,
    AccountType,
    AccountUpdate,
    AccountWithBalance,
    EnvelopeBase,
    EnvelopeSplitRequest,
    SystemEnvelopeType,
    TransactionRequest,
    TransactionType,
)


def create_account(
    session: Session,
    acc_info: AccountBase | AccountCreate,
    logged_date: date | None = None,
) -> Account:
    """Creates a new financial account and persists it in the database.

    Validates account name presence, checks for duplicates, enforces account-type specific
    field bounds, auto-links Credit Card accounts to their payment envelope, and automatically
    generates a Starting Balance transaction if an initial balance is provided.

    Args:
        session: Active SQLModel database session.
        acc_info: Account metadata including name, account type, and initial balance.
        logged_date: Optional date for the auto-generated Starting Balance transaction
            (defaults to today when omitted).

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

    # 3. Apply account-type specific validation and enforce single Cash account rule
    if acc_info.account_type == AccountType.CASH:
        if initial_balance < Decimal("0"):
            raise ValueError("Cash account balance cannot be negative")
        existing_cash = account_repo.get_cash_account(session)
        if existing_cash:
            raise ValueError(
                f"A cash account ('{existing_cash.name}') already exists. "
                "Only a single cash account is allowed."
            )
        if cleaned_name != "Cash":
            raise ValueError("The single cash account must be named 'Cash'")
        # Cash accounts do not have statement balances, interest, or due dates
        acc_info.total_statement_balance = None
        acc_info.interest_saving_balance = None
        acc_info.monthly_payment = None
        acc_info.due_date = None
    elif acc_info.account_type == AccountType.INVESTMENT:
        if initial_balance < Decimal("0"):
            raise ValueError("Investment account balance cannot be negative")
        # Investment accounts do not have statement balances, minimum payments, or due dates
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

    # 5. Auto-link Credit Card and Loan accounts to payment envelopes
    cat_id = None
    raw_cat_name = getattr(acc_info, "category_name", None)
    if isinstance(raw_cat_name, str) and raw_cat_name.strip():
        cat = category_repo.get_category_by_name(session, raw_cat_name.strip())
        if cat:
            cat_id = cat.id

    if acc_info.account_type == AccountType.CREDIT_CARD:
        cc_envelope = (
            envelope_repo.get_envelope_by_system_role(
                session, SystemEnvelopeType.CREDIT_CARD_PAYMENT
            )
            or envelope_repo.get_or_create_envelope(
                session,
                EnvelopeBase(
                    name="Credit Card Payment",
                    system_role=SystemEnvelopeType.CREDIT_CARD_PAYMENT,
                ),
                category_id=cat_id,
            )
        )
        if cat_id is not None and cc_envelope.category_id is None:
            cc_envelope.category_id = cat_id
        new_account.envelope_id = cc_envelope.id
    elif acc_info.account_type == AccountType.LOAN:
        payment_envelope = envelope_repo.get_or_create_envelope(
            session, EnvelopeBase(name=acc_info.name), category_id=cat_id
        )
        if cat_id is not None and payment_envelope.category_id is None:
            payment_envelope.category_id = cat_id
        new_account.envelope = payment_envelope

    session.commit()
    session.refresh(new_account)

    # 6. If initial balance > 0, post a Starting Balance transaction
    tx_date = logged_date or date.today()
    if initial_balance > Decimal("0.00"):
        if acc_info.account_type == AccountType.CASH:
            unassigned_env = (
                envelope_repo.get_envelope_by_system_role(
                    session, SystemEnvelopeType.UNASSIGNED
                )
                or envelope_repo.get_or_create_envelope(
                    session,
                    EnvelopeBase(
                        name="Unassigned",
                        system_role=SystemEnvelopeType.UNASSIGNED,
                    ),
                )
            )
            split = EnvelopeSplitRequest(
                amount=initial_balance,
                envelope_id=unassigned_env.id,
                envelope_name=unassigned_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Starting Balance",
                payment_method_name=cleaned_name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
                logged_date=tx_date,
            )
            transaction_repo.create_transaction(session, tx_req)
        elif acc_info.account_type == AccountType.INVESTMENT:
            adj_env = (
                envelope_repo.get_envelope_by_system_role(
                    session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
                )
                or envelope_repo.get_or_create_envelope(
                    session,
                    EnvelopeBase(
                        name="Account Adjustment",
                        system_role=SystemEnvelopeType.ACCOUNT_ADJUSTMENT,
                    ),
                )
            )
            split = EnvelopeSplitRequest(
                amount=initial_balance,
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Starting Balance",
                payment_method_name=cleaned_name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
                logged_date=tx_date,
            )
            transaction_repo.create_transaction(session, tx_req)
        elif acc_info.account_type in (
            AccountType.CREDIT_CARD,
            AccountType.LOAN,
        ):
            adj_env = (
                envelope_repo.get_envelope_by_system_role(
                    session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
                )
                or envelope_repo.get_or_create_envelope(
                    session,
                    EnvelopeBase(
                        name="Account Adjustment",
                        system_role=SystemEnvelopeType.ACCOUNT_ADJUSTMENT,
                    ),
                )
            )
            split = EnvelopeSplitRequest(
                amount=initial_balance,
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Starting Balance",
                payment_method_name=cleaned_name,
                transaction_type=TransactionType.INTEREST_CHARGE,
                splits=[split],
                logged_date=tx_date,
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

    adj_env = (
        envelope_repo.get_envelope_by_system_role(
            session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
        )
        or envelope_repo.get_or_create_envelope(
            session,
            EnvelopeBase(
                name="Account Adjustment",
                system_role=SystemEnvelopeType.ACCOUNT_ADJUSTMENT,
            ),
        )
    )

    split = EnvelopeSplitRequest(
        amount=amount,
        envelope_id=adj_env.id,
        envelope_name=adj_env.name,
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

    unassigned_env = (
        envelope_repo.get_envelope_by_system_role(
            session, SystemEnvelopeType.UNASSIGNED
        )
        or envelope_repo.get_or_create_envelope(
            session,
            EnvelopeBase(
                name="Unassigned",
                system_role=SystemEnvelopeType.UNASSIGNED,
            ),
        )
    )

    split = EnvelopeSplitRequest(
        amount=amount,
        envelope_id=unassigned_env.id,
        envelope_name=unassigned_env.name,
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


def get_account(
    session: Session, account_name: str, is_active: bool | None = None
) -> AccountWithBalance | None:
    """Fetches a single account by name with its derived balance.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account.
        is_active: Optional boolean filter. If provided, returns None if account's
            active status does not match.

    Returns:
        AccountWithBalance instance, or None if not found or filtered out.
    """
    account = account_repo.get_account_by_name(session, account_name)
    if not account or account.id is None:
        return None
    if is_active is not None and account.is_active != is_active:
        return None
    bal = account_repo.get_balance_for_account(session, account)
    env_name = None
    env_bal = None
    target_env = account.envelope
    if target_env is None and account.envelope_id is not None:
        target_env = envelope_repo.get_envelope_by_id(session, account.envelope_id)
    if target_env is not None:
        env_name = target_env.name
        env_bal = envelope_repo.get_balance_for_envelope(session, target_env)

    return AccountWithBalance(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        current_balance=bal,
        total_statement_balance=account.total_statement_balance,
        interest_saving_balance=account.interest_saving_balance,
        monthly_payment=account.monthly_payment,
        due_date=account.due_date,
        is_active=account.is_active,
        envelope_id=account.envelope_id,
        envelope_name=env_name,
        envelope_balance=env_bal,
    )


def get_all_accounts(
    session: Session,
    is_active: bool | None = True,
    account_types: list[AccountType] | None = None,
) -> List[AccountWithBalance]:
    """Fetches accounts with their dynamically derived balances.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all accounts. Defaults to True.
        account_types: Optional list of AccountType to filter by.

    Returns:
        List of AccountWithBalance instances.
    """
    return account_repo.get_accounts_with_balances(
        session, is_active=is_active, account_types=account_types
    )


def delete_account(session: Session, account_name: str) -> Account:
    """Soft-deletes (archives) an account by setting is_active=False.

    Archiving/deletion is only permitted if the account has no associated transactions
    aside from any STARTING_BALANCE transactions.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account to archive.

    Returns:
        The archived Account instance with is_active=False.

    Raises:
        ValueError: If account does not exist, is the protected default 'Cash' account,
            or has non-starting-balance transactions associated with it.
    """
    if not account_name or not account_name.strip():
        raise ValueError("Account name cannot be empty")

    name = account_name.strip()
    account = account_repo.get_account_by_name(session, name)
    if not account:
        raise ValueError(f"Account '{name}' does not exist")

    if account.name == "Cash":
        raise ValueError("Cannot delete or archive the default 'Cash' account")

    if account.id is not None and account_repo.has_non_starting_transactions(
        session, account.id
    ):
        raise ValueError(
            f"Cannot delete account '{account.name}' with associated transactions. "
            "Only accounts with no transactions or starting balance transactions can be deleted."
        )

    account.is_active = False

    # If linked to a custom payment envelope that is not a system envelope and has no balance
    if account.envelope_id is not None:
        linked_env = envelope_repo.get_envelope_by_id(session, account.envelope_id)
        if (
            linked_env is not None
            and linked_env.system_role is None
            and linked_env.name not in {"Unassigned", "Credit Card Payment", "Account Adjustment"}
        ):
            env_balance = envelope_repo.get_balance_for_envelope(session, linked_env)
            if env_balance == Decimal("0"):
                linked_env.is_active = False
                session.add(linked_env)

    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def activate_account(session: Session, account_name: str) -> Account:
    """Reactivates an archived account by setting is_active=True.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account to reactivate.

    Returns:
        The reactivated Account instance with is_active=True.

    Raises:
        ValueError: If account does not exist.
    """
    if not account_name or not account_name.strip():
        raise ValueError("Account name cannot be empty")

    name = account_name.strip()
    account = account_repo.get_account_by_name(session, name)
    if not account:
        raise ValueError(f"Account '{name}' does not exist")

    account.is_active = True

    # If linked to a custom payment envelope, reactivate it as well
    if account.envelope_id is not None:
        linked_env = envelope_repo.get_envelope_by_id(session, account.envelope_id)
        if linked_env is not None and not linked_env.is_active:
            linked_env.is_active = True
            session.add(linked_env)

    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def update_account(
    session: Session,
    target: int | str | None = None,
    account_info: AccountUpdate | None = None,
    *,
    target_name: str | None = None,
    account_id: int | None = None,
) -> Account:
    """Updates account details (name, metadata, active status).

    Args:
        session: Active SQLModel database session.
        target: Account primary key ID (int) or current name (str) of the account to update.
        account_info: AccountUpdate payload with optional new values.
        target_name: Optional keyword alias for name-based lookup.
        account_id: Optional keyword alias for ID-based lookup.

    Returns:
        The updated Account instance.

    Raises:
        ValueError: If target account does not exist, name collision occurs,
            or archiving rules are violated.
    """
    ident = target if target is not None else (account_id if account_id is not None else target_name)
    if ident is None:
        raise ValueError("Account ID or name must be provided")

    if isinstance(ident, int):
        account = account_repo.get_account_by_id(session, ident)
        if not account:
            raise ValueError(f"Account with ID {ident} does not exist")
    elif isinstance(ident, str):
        cleaned_target = ident.strip()
        if not cleaned_target:
            raise ValueError("Account name cannot be empty")
        account = account_repo.get_account_by_name(session, cleaned_target)
        if not account:
            raise ValueError(f"Account '{cleaned_target}' does not exist")
    else:
        raise ValueError("Invalid target account identifier")

    if account_info is None:
        return account

    if account_info.name is not None:
        new_name = account_info.name.strip()
        if not new_name:
            raise ValueError("Account name cannot be empty")
        if account.name == "Cash" and new_name != "Cash":
            raise ValueError("Cannot rename the default 'Cash' account")
        if new_name != account.name:
            existing = account_repo.get_account_by_name(session, new_name)
            if existing is not None and existing.id != account.id:
                raise ValueError(f"Account '{new_name}' already exists")
            account.name = new_name

    if account_info.is_active is not None:
        if account_info.is_active is False and account.is_active:
            return delete_account(session, account.name)
        elif account_info.is_active is True and not account.is_active:
            return activate_account(session, account.name)

    if account_info.total_statement_balance is not None:
        account.total_statement_balance = account_info.total_statement_balance
    if account_info.interest_saving_balance is not None:
        account.interest_saving_balance = account_info.interest_saving_balance
    if account_info.monthly_payment is not None:
        account.monthly_payment = account_info.monthly_payment
    if account_info.due_date is not None:
        account.due_date = account_info.due_date

    session.add(account)
    session.commit()
    session.refresh(account)
    return account

def make_payment(
    session: Session,
    target: str,
    amount: Decimal,
    logged_date: date | None = None,
    source: str | None = None,
    envelope_name: str | None = None,
) -> List[Transaction]:
    # fetch the account
    target_account: Account | None = account_repo.get_account_by_name(session, target)

    if not target_account:
        raise ValueError(f"account {target} does not exist")

    # ensure the account is a loan, credit card, or investment account, and active
    if target_account.account_type not in (
        AccountType.LOAN,
        AccountType.CREDIT_CARD,
        AccountType.INVESTMENT,
    ):
        raise ValueError(f"account {target} is not a loan, credit card, or investment account")

    if not target_account.is_active:
        raise ValueError(f"Cannot make payment to inactive/archived account '{target}'")

    # ensure amount is positive
    if amount <= 0:
        raise ValueError("amount has to be a positive value")

    # fetch funding envelope
    envelope: Envelope | None = None
    if target_account.account_type in (AccountType.LOAN, AccountType.CREDIT_CARD):
        envelope = target_account.envelope
        if not envelope and envelope_name:
            envelope = envelope_repo.get_envelope_by_name(session, envelope_name)
        if not envelope:
            raise ValueError(f"account {target} does not have an envelope associated to it")
    elif target_account.account_type == AccountType.INVESTMENT:
        if envelope_name:
            envelope = envelope_repo.get_envelope_by_name(session, envelope_name)
        else:
            envelope = envelope_repo.get_envelope_by_name(
                session, "Investments"
            ) or envelope_repo.get_envelope_by_name(session, "Investment")
        if not envelope:
            raise ValueError(
                "A budget envelope is required to fund an investment transfer (e.g. 'Investments')"
            )

    if envelope is None:
        raise ValueError(f"account {target} does not have an envelope associated to it")

    env_bal = envelope_repo.get_balance_for_envelope(session, envelope)
    if amount > env_bal:
        raise ValueError(f"Insufficient funds in envelope {envelope.name}: available {env_bal}, required {amount}")

    tx_date = logged_date or date.today()
    cash_acc = (
        account_repo.get_account_by_name(session, source)
        if source
        else account_repo.get_cash_account(session)
    )
    cash_name = cash_acc.name if cash_acc else "Cash"

    adj_env = envelope_repo.get_envelope_by_system_role(
        session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
    )
    adj_name = adj_env.name if adj_env else "Account Adjustment"

    merchant_label = (
        f"Transfer to {target}"
        if target_account.account_type == AccountType.INVESTMENT
        else f"Payment for {target}"
    )

    # Create a SINGLE transaction with multiple splits:
    # Split 1: Deducts from the funding envelope
    # Split 2: Offsets into Account Adjustment
    tx_req: TransactionRequest = TransactionRequest(
        merchant=merchant_label,
        note=f"{merchant_label} from {cash_name}",
        payment_method_name=cash_name,
        destination_account_name=target,
        transaction_type=TransactionType.EXPENSE,
        splits=[
            EnvelopeSplitRequest(
                amount=Decimal(-amount),
                envelope_name=envelope.name,
            ),
            EnvelopeSplitRequest(
                amount=Decimal(amount),
                envelope_name=adj_name,
            ),
        ],
        logged_date=tx_date,
    )

    single_tx: Transaction = transaction_repo.create_transaction(session, tx_req)

    session.commit()
    session.refresh(single_tx)
    return [single_tx]


def adjust_account_balance(
    session: Session,
    account_name: str,
    target_balance: Decimal,
    note: Optional[str] = None,
    envelope_name: Optional[str] = None,
) -> Transaction | None:
    """Adjusts an account's derived balance to match a real-world target balance.

    Reconciles discrepancy by logging a compensating adjustment transaction.
    For Cash accounts:
        - If target > current (surplus): logs INCOME crediting 'Unassigned'.
        - If target < current (deficit): logs EXPENSE deducting from a required
          user envelope (cannot be 'Account Adjustment').
    For Debt accounts (Credit Card, Loan):
        - If target > current (debt increased): logs INTEREST_CHARGE in
          'Account Adjustment'.
        - If target < current (debt decreased): logs INCOME in 'Account Adjustment'.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account to adjust.
        target_balance: The desired real-world balance to reconcile to.
        note: Optional custom note for the transaction.
        envelope_name: Envelope to deduct cash from if cash is reduced.
            Required if cash decreases.

    Returns:
        The created adjustment Transaction, or None if balances already match.

    Raises:
        ValueError: If account does not exist, is inactive, or if a cash
            reduction does not provide a valid non-'Account Adjustment' envelope.
    """
    if not account_name or not account_name.strip():
        raise ValueError("Account name cannot be empty")

    name = account_name.strip()
    account = account_repo.get_account_by_name(session, name)
    if not account:
        raise ValueError(f"Account '{name}' does not exist")

    if not account.is_active:
        raise ValueError(
            f"Cannot adjust balance for inactive/archived account '{name}'"
        )

    current_balance = account_repo.get_balance_for_account(session, account)
    delta = target_balance - current_balance

    if delta == Decimal("0.00"):
        return None

    if account.account_type == AccountType.CASH:
        if delta > Decimal("0.00"):
            # Cash surplus: Found money, credit to Unassigned
            unassigned_env = (
                envelope_repo.get_envelope_by_system_role(
                    session, SystemEnvelopeType.UNASSIGNED
                )
                or envelope_repo.get_or_create_envelope(
                    session,
                    EnvelopeBase(
                        name="Unassigned",
                        system_role=SystemEnvelopeType.UNASSIGNED,
                    ),
                )
            )
            split = EnvelopeSplitRequest(
                amount=delta,
                envelope_id=unassigned_env.id,
                envelope_name=unassigned_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Balance Adjustment",
                note=note or f"Balance adjustment: +{delta}",
                payment_method_name=account.name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
            )
        else:
            # Cash deficit: Deducting cash MUST come from a user-specified envelope
            if not envelope_name or not envelope_name.strip():
                raise ValueError(
                    "Cash reduction must specify an envelope to deduct funds from"
                )
            env_name = envelope_name.strip()
            target_env = envelope_repo.get_envelope_by_name(session, env_name)
            if not target_env:
                raise ValueError(f"Envelope '{env_name}' does not exist")
            if (
                target_env.system_role == SystemEnvelopeType.ACCOUNT_ADJUSTMENT
                or env_name == "Account Adjustment"
            ):
                raise ValueError(
                    "Cash reduction cannot be absorbed by 'Account Adjustment'. "
                    "It must be deducted from a budgeting envelope."
                )
            if not target_env.is_active:
                raise ValueError(f"Envelope '{env_name}' is inactive/archived")

            split = EnvelopeSplitRequest(
                amount=-abs(delta),
                envelope_id=target_env.id,
                envelope_name=target_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Balance Adjustment",
                note=note or f"Balance adjustment: -{abs(delta)}",
                payment_method_name=account.name,
                transaction_type=TransactionType.EXPENSE,
                splits=[split],
            )
    elif account.account_type == AccountType.INVESTMENT:
        adj_env = (
            envelope_repo.get_envelope_by_system_role(
                session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
            )
            or envelope_repo.get_or_create_envelope(
                session,
                EnvelopeBase(
                    name="Account Adjustment",
                    system_role=SystemEnvelopeType.ACCOUNT_ADJUSTMENT,
                ),
            )
        )
        if delta > Decimal("0.00"):
            # Investment value increased (Market gain)
            split = EnvelopeSplitRequest(
                amount=delta,
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Market Adjustment",
                note=note or f"Market value adjustment: +{delta}",
                payment_method_name=account.name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
            )
        else:
            # Investment value decreased (Market loss)
            split = EnvelopeSplitRequest(
                amount=-abs(delta),
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Market Adjustment",
                note=note or f"Market value adjustment: -{abs(delta)}",
                payment_method_name=account.name,
                transaction_type=TransactionType.EXPENSE,
                splits=[split],
            )
    else:
        # Debt account: CREDIT_CARD or LOAN
        adj_env = (
            envelope_repo.get_envelope_by_system_role(
                session, SystemEnvelopeType.ACCOUNT_ADJUSTMENT
            )
            or envelope_repo.get_or_create_envelope(
                session,
                EnvelopeBase(
                    name="Account Adjustment",
                    system_role=SystemEnvelopeType.ACCOUNT_ADJUSTMENT,
                ),
            )
        )
        if delta > Decimal("0.00"):
            # Debt increased: You owe more
            split = EnvelopeSplitRequest(
                amount=delta,
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Balance Adjustment",
                note=note or f"Balance adjustment: +{delta} debt",
                payment_method_name=account.name,
                transaction_type=TransactionType.INTEREST_CHARGE,
                splits=[split],
            )
        else:
            # Debt decreased: You owe less
            split = EnvelopeSplitRequest(
                amount=abs(delta),
                envelope_id=adj_env.id,
                envelope_name=adj_env.name,
            )
            tx_req = TransactionRequest(
                merchant="Balance Adjustment",
                note=note or f"Balance adjustment: -{abs(delta)} debt",
                payment_method_name=account.name,
                transaction_type=TransactionType.INCOME,
                splits=[split],
            )

    tx = transaction_repo.create_transaction(session, tx_req)
    session.commit()
    session.refresh(tx)
    return tx


archive_account = delete_account
