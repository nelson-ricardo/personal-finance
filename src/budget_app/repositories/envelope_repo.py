from budget_app.models.envelope import Envelope

from sqlmodel import Session, select

def get_envelope_by_name(session: Session, envelope_name: str) -> Envelope | None:
    stmt = select(Envelope).where(Envelope.name == envelope_name)
    result = session.exec(stmt)
    ret_envelope = result.one_or_none()
    return ret_envelope