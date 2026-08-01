from sqlmodel import Session

from budget_app.models import envelope as envelope_db
from budget_app.schemas import envelope as envelope_schema

def create_envelope(session: Session, envelope_info: envelope_schema.EnvelopeBase) -> envelope_db.Envelope:
    new_envelope = envelope_db.Envelope.model_validate(envelope_info)

    session.add(new_envelope)
    session.commit()
    session.refresh(new_envelope)

    return new_envelope