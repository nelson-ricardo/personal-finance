"""EnvelopeSplit repository for database operations on individual EnvelopeSplit entries."""

from sqlmodel import Session

from budget_app.models import Envelope, EnvelopeSplit
from budget_app.repositories import envelope_repo
from budget_app.schemas import EnvelopeSplitRequest


def add_envelope_split(
    session: Session, entry: EnvelopeSplitRequest
) -> EnvelopeSplit:
    """Creates and stages a single EnvelopeSplit entry attached to an envelope.

    Args:
        session: Active SQLModel database session.
        entry: EnvelopeSplitRequest schema containing signed amount and envelope name.

    Returns:
        The staged EnvelopeSplit instance attached to the resolved Envelope.

    Raises:
        ValueError: If the envelope specified by envelope_name does not exist.
    """
    assigned_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, entry.envelope_name
    )
    if not assigned_envelope:
        raise ValueError(f"Envelope {entry.envelope_name} does not exist")

    new_entry = EnvelopeSplit(
        amount=entry.amount,
        envelope=assigned_envelope,
    )

    session.add(new_entry)
    return new_entry


# Backward-compatible alias
add_ledger_entry = add_envelope_split
