from sqlmodel import Session
from budget_app.db.engine import engine
from budget_app.services import account_service, envelope_service
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import envelope, account

def init_db(session: Session) -> None:
    if not envelope_repo.get_envelope_by_name(session, "Unassigned"):
        envelope_service.create_envelope(
            session, 
            envelope.EnvelopeBase(name="Unassigned",note="default bucket for money coming in")
        )
        print("Unassigned envelope created.")

    if not envelope_repo.get_envelope_by_name(session, "Credit Card Payment"):
        envelope_service.create_envelope(
            session,
            envelope.EnvelopeBase(name="Credit Card Payment", note="holds money allocated to pay off credit card balance")
        )
        print("Credit card payment envelope created.")

    if not account_repo.get_account_by_name(session, "Cash"):
        account_service.create_account(
            session,
            account.AccountBase(name="Cash", account_type=account.AccountType.CASH)
        )
        print("Created default Cash account.")

    print("Database initialization complete.")

if __name__ == "__main__":
    with Session(engine) as session:
        init_db(session)