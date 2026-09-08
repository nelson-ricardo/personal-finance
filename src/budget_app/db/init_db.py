"""Database initialization and seeding script.

Creates essential system records if they do not already exist:
- 'Unassigned' envelope: Default bucket for unallocated income.
- 'Credit Card Payment' envelope: Holding envelope for funds moved to pay credit card bills.
- 'Cash' account: Default cash payment account.
"""

from sqlmodel import Session

from budget_app.db import engine
from budget_app.repositories import account_repo, category_repo, envelope_repo
from budget_app.schemas import (
    AccountBase,
    AccountType,
    EnvelopeBase,
    EnvelopeCategoryBase,
)
from budget_app.services import account_service, envelope_service

DEFAULT_CATEGORIES = [
    ("Fixed Monthly Expenses", 1),
    ("Variable Monthly Expenses", 2),
    ("Savings", 3),
    ("Wants", 4),
    ("System", 5),
]


def init_db(session: Session) -> None:
    """Initializes the database with required default categories, envelopes, and accounts.

    Args:
        session: Active SQLModel database session.
    """
    # 1. Seed default category groups
    for cat_name, order_idx in DEFAULT_CATEGORIES:
        category_repo.get_or_create_category(
            session,
            EnvelopeCategoryBase(name=cat_name, order_index=order_idx, is_active=True),
        )
    session.commit()

    # Fetch seeded categories for linking
    system_cat = category_repo.get_category_by_name(session, "System")
    fixed_cat = category_repo.get_category_by_name(session, "Fixed Monthly Expenses")

    # 2. Ensure the default 'Unassigned' income envelope exists under 'System'
    unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
    if not unassigned:
        envelope_service.create_envelope(
            session,
            EnvelopeBase(name="Unassigned", note="default bucket for money coming in"),
            category_name="System",
        )
        print("Unassigned envelope created.")
    elif unassigned.category_id is None and system_cat:
        unassigned.category_id = system_cat.id
        session.add(unassigned)
        session.commit()

    # 3. Ensure the default 'Credit Card Payment' holding envelope exists under 'Fixed Monthly Expenses'
    cc_envelope = envelope_repo.get_envelope_by_name(session, "Credit Card Payment")
    if not cc_envelope:
        envelope_service.create_envelope(
            session,
            EnvelopeBase(
                name="Credit Card Payment",
                note="holds money allocated to pay off credit card balance",
            ),
            category_name="Fixed Monthly Expenses",
        )
        print("Credit card payment envelope created.")
    elif cc_envelope.category_id is None and fixed_cat:
        cc_envelope.category_id = fixed_cat.id
        session.add(cc_envelope)
        session.commit()

    # 4. Ensure the default 'Account Adjustment' system envelope exists under 'System'
    adj_envelope = envelope_repo.get_envelope_by_name(session, "Account Adjustment")
    if not adj_envelope:
        envelope_service.create_envelope(
            session,
            EnvelopeBase(
                name="Account Adjustment",
                note="system envelope for absorbing account-only balance adjustments",
            ),
            category_name="System",
        )
        print("Account Adjustment envelope created.")
    elif adj_envelope.category_id is None and system_cat:
        adj_envelope.category_id = system_cat.id
        session.add(adj_envelope)
        session.commit()

    # 5. Ensure the primary 'Cash' account exists
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

