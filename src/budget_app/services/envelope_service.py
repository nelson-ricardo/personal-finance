from sqlmodel import Session

from budget_app.models import envelope as envelope_db
from budget_app.schemas import envelope as envelope_schema
from budget_app.repositories.envelope_repo import create_envelope as create_envelope_db

def create_envelope(session: Session, envelope_info: envelope_schema.EnvelopeBase) -> envelope_db.Envelope:
    new_envelope = create_envelope_db(session, envelope_info)
    session.commit()
    session.refresh(new_envelope)

    return new_envelope