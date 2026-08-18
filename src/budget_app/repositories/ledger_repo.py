from sqlmodel import Session

from budget_app.models import Ledger, Envelope
from budget_app.schemas import LedgerRequest
from budget_app.repositories import envelope_repo


def add_ledger_entry(
    session: Session, entry: LedgerRequest
) -> Ledger:
    assigned_envelope: Envelope | None = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
    if not assigned_envelope:
        raise ValueError(f"Envelope {entry.envelope_name} does not exist")
    
    new_entry = Ledger(
        amount=entry.amount,
        envelope= assigned_envelope
    )

    session.add(new_entry)
    return new_entry
