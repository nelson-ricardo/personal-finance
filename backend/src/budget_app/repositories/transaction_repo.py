"""Transaction repository for database operations on Transaction and child Ledger entities."""

from datetime import date

from sqlmodel import Session, col, select

from budget_app.models import EnvelopeSplit, Transaction
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import TransactionRequest, TransactionType


def create_transaction(
    session: Session, transaction_info: TransactionRequest
) -> Transaction:
    """Creates and stages a master Transaction record with its child EnvelopeSplit entries.

    Resolves payment method and envelope references, binds EnvelopeSplit entries, and stages the
    Transaction in the current session.

    Args:
        session: Active SQLModel database session.
        transaction_info: TransactionRequest containing merchant, dates, account name, and envelope splits.

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

    # 2. Resolve each envelope and instantiate EnvelopeSplit entries
    resolved_splits = []
    for entry in transaction_info.splits:
        env = None
        if entry.envelope_id is not None:
            env = envelope_repo.get_envelope_by_id(session, entry.envelope_id)
            if not env:
                raise ValueError(f"Envelope ID {entry.envelope_id} does not exist.")
        elif entry.envelope_name:
            env = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
            if not env:
                raise ValueError(f"Envelope {entry.envelope_name} does not exist.")
        else:
            raise ValueError("Split must specify envelope_name or envelope_id.")
        resolved_splits.append((entry, env))

    splits_db = [
        EnvelopeSplit(amount=entry.amount, envelope=env)
        for entry, env in resolved_splits
    ]

    # Resolve destination account if provided
    dest_account = None
    dest_name = getattr(transaction_info, "destination_account_name", None)
    if dest_name:
        dest_account = account_repo.get_account_by_name(session, dest_name)
        if not dest_account:
            raise ValueError(
                f"Destination account '{dest_name}' does not exist."
            )

    # 3. Create master Transaction entity bound to account and splits
    transaction: Transaction = Transaction(
        merchant=transaction_info.merchant,
        logged_date=transaction_info.logged_date,
        posted_date=transaction_info.posted_date,
        is_reconciled=transaction_info.is_reconciled,
        account=account,
        destination_account_id=dest_account.id if dest_account else None,
        splits=splits_db,
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
    exclude_reversed: bool = False,
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
        exclude_reversed: If True, excludes both REVERSAL type transactions and transactions
            marked with [REVERSED] in their note.

    Returns:
        List of matching Transaction instances ordered by logged_date descending.
    """
    stmt = select(Transaction)

    if account_id is not None:
        stmt = stmt.where(
            (col(Transaction.payment_method_id) == account_id)
            | (col(Transaction.destination_account_id) == account_id)
        )

    if date_from is not None:
        stmt = stmt.where(col(Transaction.logged_date) >= date_from)

    if date_to is not None:
        stmt = stmt.where(col(Transaction.logged_date) <= date_to)

    if transaction_types is not None:
        stmt = stmt.where(col(Transaction.transaction_type).in_(transaction_types))

    if exclude_reversed:
        stmt = stmt.where(col(Transaction.transaction_type) != TransactionType.REVERSAL)
        stmt = stmt.where(
            (col(Transaction.note).is_(None)) | (~col(Transaction.note).ilike("%[REVERSED]%"))
        )

    if envelope_id is not None:
        subquery = select(EnvelopeSplit.transaction_id).where(
            col(EnvelopeSplit.envelope_id) == envelope_id
        )
        if (
            exclude_balancing_for_envelope_id is not None
            and envelope_id == exclude_balancing_for_envelope_id
        ):
            subquery = subquery.where(col(EnvelopeSplit.amount) <= 0)

        stmt = stmt.where(col(Transaction.id).in_(subquery))



    stmt = stmt.order_by(
        col(Transaction.logged_date).desc(),
        col(Transaction.id).desc(),
    )

    if limit is not None:
        stmt = stmt.limit(limit)

    results = session.exec(stmt).all()
    return list(results)


def get_transaction_by_id(session: Session, transaction_id: int) -> Transaction | None:
    """Fetches a single Transaction by its primary key ID.

    Args:
        session: Active SQLModel database session.
        transaction_id: Primary key integer ID.

    Returns:
        The matching Transaction instance if found, otherwise None.
    """
    return session.get(Transaction, transaction_id)



