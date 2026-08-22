from decimal import Decimal

from sqlmodel import Session, func, select

from budget_app.models import Envelope, Ledger
from budget_app.schemas import EnvelopeBase


def get_envelope_by_name(session: Session, envelope_name: str) -> Envelope | None:
    stmt = select(Envelope).where(Envelope.name == envelope_name)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope


def get_envelope_by_id(session: Session, envelope_id: int) -> Envelope | None:
    stmt = select(Envelope).where(Envelope.id == envelope_id)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope


def create_envelope(session: Session, new_envelope: EnvelopeBase) -> Envelope:
    """
        Strictly creates a new envelope. Checks if it exists, if it does raises
        ValueError
    """
    test_env: Envelope | None = get_envelope_by_name(session, new_envelope.name)

    if not test_env:
        ret_envelope: Envelope = Envelope.model_validate(new_envelope)
        session.add(ret_envelope)
        return ret_envelope
    else:
        raise ValueError("Envelope already exists")

def get_or_create_envelope(session: Session, new_envelope: EnvelopeBase) -> Envelope:
    """
        Checks if the envelope already exists in the system (get it by name)
        if there is one, return that envelope instead, otherwise
        create the envelope, add it to the session, and return it
    """
    ret_envelope: Envelope | None = get_envelope_by_name(session, new_envelope.name)
    if not ret_envelope:
        ret_envelope = Envelope.model_validate(new_envelope)
        session.add(ret_envelope)

    return ret_envelope


def get_balance_for_envelope(session: Session, cur_envelope: Envelope) -> Decimal:
    statement = select(func.sum(Ledger.amount)).where(
        Ledger.envelope_id == cur_envelope.id
    )

    result = session.exec(statement).one()
    return result
