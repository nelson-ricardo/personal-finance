"""Account service for account creation, validation, and automated envelope linking."""

from decimal import Decimal
from sqlmodel import Session

from budget_app.models import Account
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import AccountBase, AccountType, EnvelopeBase


def create_account(
    session: Session, acc_info: AccountBase
) -> Account:
    """Creates a new financial account and persists it in the database.

    Validates account name presence, checks for duplicates, enforces account-type specific
    field bounds, and auto-links Credit Card accounts to their payment envelope.

    Args:
        session: Active SQLModel database session.
        acc_info: Account metadata including name, account type, and initial balance.

    Returns:
        The newly created and refreshed Account instance.

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

    # 3. Apply account-type specific validation and sanitize irrelevant fields
    if acc_info.account_type == AccountType.CASH:
        if acc_info.current_balance < Decimal("0"):
            raise ValueError("Cash account balance cannot be negative")
        # Cash accounts do not have statement balances, interest, or due dates
        acc_info.total_statement_balance = None
        acc_info.interest_saving_balance = None
        acc_info.monthly_payment = None
        acc_info.due_date = None
    elif acc_info.account_type in (AccountType.CREDIT_CARD, AccountType.LOAN):
        if acc_info.current_balance < Decimal("0"):
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
    return new_account

