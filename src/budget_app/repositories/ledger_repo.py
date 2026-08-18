from sqlmodel import Session

from budget_app.models import Ledger
from budget_app.schemas import LedgerRequest


def add_ledger_entry(
    session: Session, entry: LedgerRequest
) -> Ledger:
    new_entry = Ledger.model_validate(entry)

    session.add(new_entry)
    return new_entry
