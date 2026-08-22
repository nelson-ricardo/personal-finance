"""Transaction repository for database operations on Transaction and child Ledger entities."""

from datetime import date
from sqlmodel import Session, col, select

from budget_app.models import Ledger, Transaction
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import TransactionRequest, TransactionType


def create_transaction(
    session: Session, transaction_info: TransactionRequest
) -> Transaction:
    """Creates and stages a master Transaction record with its child Ledger split entries.

    Resolves payment method and envelope references, binds Ledger entries, and stages the
    Transaction in the current session.

    Args:
        session: Active SQLModel database session.
        transaction_info: TransactionRequest containing merchant, dates, account name, and ledger splits.

    Returns:
        The staged Transaction instance.

    Raises:
        ValueError: If the specified account or any referenced envelope does not exist.
    """
    # 1. Resolve the payment method account by name
    account = account_repo.get_account_by_name(
        session, transaction_info.payment_method_name
    )
    if not account:
        raise ValueError(
            f"Account {transaction_info.payment_method_name} does not exist."
        )

    # 2. Resolve each envelope and instantiate Ledger entries
    envelopes_by_name = {}
    for entry in transaction_info.ledger_entries:
        env = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
        if not env:
            raise ValueError(f"Envelope {entry.envelope_name} does not exist.")
        envelopes_by_name[entry.envelope_name] = env

    ledger_entries_db = [
        Ledger(
            amount=entry.amount, envelope=envelopes_by_name[entry.envelope_name]
        )
        for entry in transaction_info.ledger_entries
    ]

    # 3. Create master Transaction entity bound to account and ledger splits
    transaction: Transaction = Transaction(
        merchant=transaction_info.merchant,
        logged_date=transaction_info.logged_date,
        posted_date=transaction_info.posted_date,
        is_reconciled=transaction_info.is_reconciled,
        account=account,
        entries=ledger_entries_db,
        note=transaction_info.note,
        transaction_type=transaction_info.transaction_type,
    )

    session.add(transaction)
    return transaction



def get_transactions(
    session: Session,
    *,
    account_id: int | None = None,
    envelope_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int | None = None,
    transaction_types: list[TransactionType] | None = None,
    exclude_balancing_for_envelope_id: int | None = None,
) -> list[Transaction]:
    """Queries transactions from the database based on the provided filters.

    Args:
        session: Active SQLModel database session.
        account_id: Optional ID of the payment account to filter by.
        envelope_id: Optional ID of the envelope to filter by.
        date_from: Optional minimum logged date inclusive.
        date_to: Optional maximum logged date inclusive.
        limit: Optional maximum number of transactions to return.
        transaction_types: Optional list of TransactionType enums to filter by.
        exclude_balancing_for_envelope_id: Optional envelope ID for which credit card
            balancing entries (amount > 0) should not qualify a transaction.

    Returns:
        List of matching Transaction instances ordered by logged_date descending.
    """
    stmt = select(Transaction)

    if account_id is not None:
        stmt = stmt.where(col(Transaction.payment_method_id) == account_id)

    if date_from is not None:
        stmt = stmt.where(col(Transaction.logged_date) >= date_from)

    if date_to is not None:
        stmt = stmt.where(col(Transaction.logged_date) <= date_to)

    if transaction_types is not None:
        stmt = stmt.where(col(Transaction.transaction_type).in_(transaction_types))

    if envelope_id is not None:
        subquery = select(Ledger.transaction_id).where(
            col(Ledger.envelope_id) == envelope_id
        )
        if (
            exclude_balancing_for_envelope_id is not None
            and envelope_id == exclude_balancing_for_envelope_id
        ):
            subquery = subquery.where(col(Ledger.amount) <= 0)

        stmt = stmt.where(col(Transaction.id).in_(subquery))

    stmt = stmt.order_by(
        col(Transaction.logged_date).desc(),
        col(Transaction.id).desc(),
    )

    if limit is not None:
        stmt = stmt.limit(limit)

    results = session.exec(stmt).all()
    return list(results)


