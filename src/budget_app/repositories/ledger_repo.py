from sqlmodel import Session

from budget_app.models import ledger
from budget_app.schemas import ledger as ledger_schema


def add_ledger_entry(
    session: Session, entry: ledger_schema.LedgerRequest
) -> ledger.Ledger:
    new_entry = ledger.Ledger.model_validate(entry)

    session.add(new_entry)
    return new_entry
