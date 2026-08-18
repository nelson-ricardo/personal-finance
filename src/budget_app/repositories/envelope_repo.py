from decimal import Decimal

from sqlmodel import Session, func, select

from budget_app.models import Envelope, Ledger
from budget_app.schemas import EnvelopeBase


def get_envelope_by_name(session: Session, envelope_name: str) -> Envelope | None:
    stmt = select(Envelope).where(Envelope.name == envelope_name)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope


def create_envelope(session: Session, new_envelope: EnvelopeBase) -> Envelope:
    new_envelope = Envelope.model_validate(new_envelope)
    session.add(new_envelope)
    return new_envelope


def get_balance_for_envelope(session: Session, cur_envelope: Envelope) -> Decimal:
    statement = select(func.sum(Ledger.amount)).where(
        Ledger.envelope_id == cur_envelope.id
    )

    result = session.exec(statement).one()
    return result
