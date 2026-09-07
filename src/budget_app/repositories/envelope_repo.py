"""Envelope repository for database operations on the Envelope entity."""

from decimal import Decimal
from typing import List

from sqlmodel import Session, func, select

from budget_app.models import Envelope, EnvelopeSplit, Ledger
from budget_app.schemas import EnvelopeBase


def get_envelope_by_name(session: Session, envelope_name: str) -> Envelope | None:
    """Fetches an envelope by its unique name.

    Args:
        session: Active SQLModel database session.
        envelope_name: Name of the envelope to look up.

    Returns:
        The matching Envelope instance if found, otherwise None.
    """
    stmt = select(Envelope).where(Envelope.name == envelope_name)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope


def get_envelope_by_id(session: Session, envelope_id: int) -> Envelope | None:
    """Fetches an envelope by its primary key ID.

    Args:
        session: Active SQLModel database session.
        envelope_id: Integer ID of the envelope.

    Returns:
        The matching Envelope instance if found, otherwise None.
    """
    stmt = select(Envelope).where(Envelope.id == envelope_id)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope


def create_envelope(session: Session, new_envelope: EnvelopeBase) -> Envelope:
    """Strictly creates a new envelope, raising an error if it already exists.

    Args:
        session: Active SQLModel database session.
        new_envelope: EnvelopeBase schema containing envelope data.

    Returns:
        The newly created Envelope instance staged in the session.

    Raises:
        ValueError: If an envelope with the given name already exists.
    """
    test_env: Envelope | None = get_envelope_by_name(session, new_envelope.name)

    if not test_env:
        ret_envelope: Envelope = Envelope.model_validate(new_envelope)
        session.add(ret_envelope)
        return ret_envelope
    else:
        raise ValueError("Envelope already exists")


def get_or_create_envelope(session: Session, new_envelope: EnvelopeBase) -> Envelope:
    """Retrieves an existing envelope by name, or creates and stages a new one if not found.

    Args:
        session: Active SQLModel database session.
        new_envelope: EnvelopeBase schema with name and attributes.

    Returns:
        The existing or newly staged Envelope instance.
    """
    ret_envelope: Envelope | None = get_envelope_by_name(session, new_envelope.name)
    if not ret_envelope:
        ret_envelope = Envelope.model_validate(new_envelope)
        session.add(ret_envelope)

    return ret_envelope


def get_balance_for_envelope(session: Session, cur_envelope: Envelope) -> Decimal:
    """Calculates the current net balance of an envelope by summing all its split entries.

    If an envelope has no associated split entries, its balance is $0.

    Args:
        session: Active SQLModel database session.
        cur_envelope: Envelope instance whose balance is to be aggregated.

    Returns:
        The sum of all EnvelopeSplit.amount entries associated with the envelope as Decimal,
        or Decimal("0") if there are no split entries.
    """
    statement = select(func.sum(EnvelopeSplit.amount)).where(
        EnvelopeSplit.envelope_id == cur_envelope.id
    )

    result = session.exec(statement).one()
    if result is None:
        return Decimal("0")
    return Decimal(result)


def get_envelopes(session: Session, is_active: bool | None = None) -> List[Envelope]:
    """Fetches envelopes from the database, optionally filtered by active status.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all envelopes.

    Returns:
        List of matching Envelope instances ordered by name.
    """
    stmt = select(Envelope)
    if is_active is not None:
        stmt = stmt.where(Envelope.is_active == is_active)

    stmt = stmt.order_by(Envelope.name)
    results = session.exec(stmt).all()
    return list(results)


def has_splits(session: Session, envelope_id: int) -> bool:
    """Checks whether an envelope has any associated split entries.

    Args:
        session: Active SQLModel database session.
        envelope_id: Integer ID of the envelope.

    Returns:
        True if at least one EnvelopeSplit entry exists for this envelope, False otherwise.
    """
    stmt = select(EnvelopeSplit.id).where(EnvelopeSplit.envelope_id == envelope_id).limit(1)
    return session.exec(stmt).first() is not None


# Backward-compatible alias
has_ledger_entries = has_splits


def delete_envelope(session: Session, envelope: Envelope) -> None:
    """Deletes an envelope entity from the session.

    Args:
        session: Active SQLModel database session.
        envelope: Envelope instance to delete.
    """
    session.delete(envelope)