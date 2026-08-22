"""Ledger repository for database operations on individual Ledger entries."""

from sqlmodel import Session

from budget_app.models import Envelope, Ledger
from budget_app.repositories import envelope_repo
from budget_app.schemas import LedgerRequest


def add_ledger_entry(
    session: Session, entry: LedgerRequest
) -> Ledger:
    """Creates and stages a single Ledger entry attached to an envelope.

    Args:
        session: Active SQLModel database session.
        entry: LedgerRequest schema containing signed amount and envelope name.

    Returns:
        The staged Ledger instance attached to the resolved Envelope.

    Raises:
        ValueError: If the envelope specified by envelope_name does not exist.
    """
    assigned_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, entry.envelope_name
    )
    if not assigned_envelope:
        raise ValueError(f"Envelope {entry.envelope_name} does not exist")

    new_entry = Ledger(
        amount=entry.amount,
        envelope=assigned_envelope,
    )

    session.add(new_entry)
    return new_entry

