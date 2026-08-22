"""Database initialization and seeding script.

Creates essential system records if they do not already exist:
- 'Unassigned' envelope: Default bucket for unallocated income.
- 'Credit Card Payment' envelope: Holding envelope for funds moved to pay credit card bills.
- 'Cash' account: Default cash payment account.
"""

from sqlmodel import Session

from budget_app.db import engine
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import AccountBase, AccountType, EnvelopeBase
from budget_app.services import account_service, envelope_service


def init_db(session: Session) -> None:
    """Initializes the database with required default envelopes and accounts.

    Args:
        session: Active SQLModel database session.
    """
    # 1. Ensure the default 'Unassigned' income envelope exists
    if not envelope_repo.get_envelope_by_name(session, "Unassigned"):
        envelope_service.create_envelope(
            session,
            EnvelopeBase(
                name="Unassigned", note="default bucket for money coming in"
            ),
        )
        print("Unassigned envelope created.")

    # 2. Ensure the default 'Credit Card Payment' holding envelope exists
    if not envelope_repo.get_envelope_by_name(session, "Credit Card Payment"):
        envelope_service.create_envelope(
            session,
            EnvelopeBase(
                name="Credit Card Payment",
                note="holds money allocated to pay off credit card balance",
            ),
        )
        print("Credit card payment envelope created.")

    # 3. Ensure the primary 'Cash' account exists
    if not account_repo.get_account_by_name(session, "Cash"):
        account_service.create_account(
            session,
            AccountBase(name="Cash", account_type=AccountType.CASH),
        )
        print("Created default Cash account.")

    print("Database initialization complete.")


if __name__ == "__main__":
    with Session(engine) as session:
        init_db(session)

