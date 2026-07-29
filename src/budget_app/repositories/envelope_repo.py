from budget_app.models.envelope import Envelope

from sqlmodel import Session, select

def get_envelope_by_name(session: Session, envelope_name: str) -> Envelope:
    statement = select(Envelope).where(Envelope.name == envelope_name)
    result = session.exec(statement)
    ret_envelope: Envelope = result.one()
    return ret_envelope