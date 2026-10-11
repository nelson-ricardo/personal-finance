"""Realistic development seed data: "Alex" budgeting for roughly ten weeks.

Everything is created through the service layer so every business rule and
constraint is honored. The story starts from the production ``init_db`` state
(default categories, system envelopes, and the ``Cash`` account) and the dates
are anchored to the calendar by :class:`~budget_app.dev.timeline.Timeline`.

Money rules respected by the story (the services raise if any is broken):
* ``Unassigned`` covers each envelope assignment.
* The shared ``Credit Card Payment`` envelope covers each card payment.
* A loan's own envelope is funded before each loan payment.

One purchase deliberately overspends ``Dining Out`` (the only negative
envelope in the final state), mirroring what happens to real users.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from budget_app.dev.timeline import Timeline
from budget_app.models import Envelope
from budget_app.repositories import envelope_repo
from budget_app.schemas import (
    AccountCreate,
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    FinancedTransaction,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import (
    account_service,
    envelope_service,
    transaction_service,
)

CHASE = "Chase Sapphire"
AMEX = "Amex Blue"
LOAN = "Honda Civic Loan"
CASH = "Cash"

ENVELOPES: list[tuple[str, str, str | None]] = [
    # (name, category, note)
    ("Rent", "Fixed Monthly Expenses", "Monthly apartment rent"),
    ("Utilities", "Fixed Monthly Expenses", "Electric and water"),
    ("Phone Bill", "Fixed Monthly Expenses", None),
    ("Groceries", "Variable Monthly Expenses", None),
    ("Gas", "Variable Monthly Expenses", "Car fuel"),
    ("Household", "Variable Monthly Expenses", "Cleaning, home goods"),
    ("Skincare", "Variable Monthly Expenses", None),
    ("Dining Out", "Wants", None),
    ("Entertainment", "Wants", "Streaming, movies, books"),
    ("Emergency Fund", "Savings", "3 months of expenses"),
    ("Vacation", "Savings", None),
]

# Dining Out is the one envelope Alex overspends on purpose.
OVERSPENT_ENVELOPE = "Dining Out"
EXPECTED_LOAN_BALANCE = Decimal("7545.00")


def _d(value: str) -> Decimal:
    return Decimal(value)


def _spend(
    session: Session,
    merchant: str,
    account: str,
    when: date,
    splits: dict[str, str],
    note: str | None = None,
) -> None:
    """Records an expense; ``splits`` maps envelope name -> positive amount spent."""
    transaction_service.add_reg_transaction(
        session,
        TransactionRequest(
            merchant=merchant,
            logged_date=when,
            note=note,
            payment_method_name=account,
            transaction_type=TransactionType.EXPENSE,
            splits=[
                EnvelopeSplitRequest(envelope_name=env, amount=-_d(amount))
                for env, amount in splits.items()
            ],
        ),
    )


def _budget(session: Session, when: date, amounts: dict[str, str]) -> None:
    """Assigns money from ``Unassigned`` into envelopes on ``when``."""
    for envelope, amount in amounts.items():
        envelope_service.assign_to_envelope(
            session, envelope, _d(amount), logged_date=when
        )


def seed(session: Session, today: date | None = None) -> None:
    """Populates an initialised database with Alex's story.

    Args:
        session: Active session on a database that already ran ``init_db``.
        today: Override for "today" (used by tests); defaults to the real date.

    Raises:
        AssertionError: If the finished story violates its expected end state.
    """
    t = Timeline(today)

    # --- Accounts -----------------------------------------------------------
    account_service.create_account(
        session,
        AccountCreate(
            name=CHASE,
            account_type=AccountType.CREDIT_CARD,
            due_date=t.next_day_of_month(25),
        ),
    )
    account_service.create_account(
        session,
        AccountCreate(
            name=AMEX,
            account_type=AccountType.CREDIT_CARD,
            due_date=t.next_day_of_month(19),
        ),
    )
    account_service.create_account(
        session,
        AccountCreate(
            name=LOAN,
            account_type=AccountType.LOAN,
            starting_balance=_d("8400.00"),
            monthly_payment=_d("285.00"),
            due_date=t.next_day_of_month(10),
        ),
        logged_date=t.on(0, 1),
    )

    # --- Envelopes ------------------------------------------------------------
    for name, category, note in ENVELOPES:
        envelope_service.create_envelope(
            session, EnvelopeBase(name=name, note=note), category_name=category
        )

    # --- Cycle 1: paycheck #1 (Aug 7) --------------------------------------------
    envelope_service.add_to_cash(
        session, _d("2400.00"), "Acme Corp Paycheck", logged_date=t.on(0, 7)
    )
    _budget(
        session,
        t.on(0, 7),
        {
            "Rent": "1200", "Utilities": "150", "Phone Bill": "70", LOAN: "285",
            "Groceries": "250", "Gas": "60", "Household": "50", "Dining Out": "60",
            "Skincare": "40", "Entertainment": "40", "Emergency Fund": "150",
            "Vacation": "40",
        },
    )
    _spend(session, "Landlord", CASH, t.on(0, 8), {"Rent": "1200.00"})
    _spend(session, "Trader Joe's", CASH, t.on(0, 9), {"Groceries": "58.40"})
    _spend(
        session, "Target", CHASE, t.on(0, 10),
        {"Groceries": "41.25", "Skincare": "27.80", "Household": "18.99"},
    )
    account_service.make_payment(session, LOAN, _d("285.00"), logged_date=t.on(0, 10))
    _spend(session, "City Electric", CASH, t.on(0, 12), {"Utilities": "92.15"})
    _spend(session, "Shell", CHASE, t.on(0, 13), {"Gas": "38.50"})
    _spend(session, "Netflix", CHASE, t.on(0, 14), {"Entertainment": "15.49"})
    _spend(session, "Chipotle", AMEX, t.on(0, 15), {"Dining Out": "14.75"})
    _spend(session, "Whole Foods", CHASE, t.on(0, 16), {"Groceries": "76.30"})
    _spend(session, "Verizon", AMEX, t.on(0, 17), {"Phone Bill": "70.00"})

    # --- Cycle 2: paycheck #2 (Aug 21) -------------------------------------------
    envelope_service.add_to_cash(
        session, _d("2400.00"), "Acme Corp Paycheck", logged_date=t.on(0, 21)
    )
    _budget(
        session,
        t.on(0, 21),
        {
            "Groceries": "220", "Gas": "60", "Household": "50", "Dining Out": "60",
            "Skincare": "50", "Entertainment": "40", "Emergency Fund": "400",
            "Vacation": "300",
        },
    )
    _spend(
        session, "Costco", CASH, t.on(0, 22),
        {"Groceries": "112.30", "Household": "46.75"},
    )
    _spend(session, "Olive Garden", CHASE, t.on(0, 23), {"Dining Out": "54.20"})
    _spend(session, "Chevron", CASH, t.on(0, 24), {"Gas": "40.00"})
    _spend(
        session, "Amazon", AMEX, t.on(0, 25),
        {"Household": "33.40", "Entertainment": "17.99"},
        note="Storage bin and a paperback",
    )
    _spend(session, "AMC Theatres", CASH, t.on(0, 28), {"Entertainment": "28.00"})
    _spend(session, "Sephora", AMEX, t.on(0, 29), {"Skincare": "58.00"})
    envelope_service.transfer_between_envelopes(
        session, "Dining Out", "Groceries", _d("25.00"), logged_date=t.on(0, 30)
    )
    account_service.add_interest_charge(
        session, CHASE, _d("9.85"), logged_date=t.on(0, 31)
    )
    account_service.make_payment(session, CHASE, _d("200.00"), logged_date=t.on(1, 2))

    # --- Cycle 3: paycheck #3 (Sep 4) --------------------------------------------
    envelope_service.add_to_cash(
        session, _d("2400.00"), "Acme Corp Paycheck", logged_date=t.on(1, 4)
    )
    _budget(
        session,
        t.on(1, 4),
        {
            "Rent": "1200", "Utilities": "150", "Phone Bill": "70", LOAN: "285",
            "Groceries": "220", "Gas": "60", "Household": "40", "Dining Out": "60",
            "Emergency Fund": "300", "Vacation": "200",
        },
    )
    _spend(session, "Landlord", CASH, t.on(1, 5), {"Rent": "1200.00"})
    transaction_service.add_financed_transaction(
        session,
        FinancedTransaction(
            merchant="Best Buy Laptop",
            term=12,
            amount=_d("1200.00"),
            payment_method_name=AMEX,
            logged_date=t.on(1, 6),
            note="New laptop on a 12-month plan",
        ),
    )
    _spend(session, "City Electric", CASH, t.on(1, 8), {"Utilities": "88.40"})
    _spend(
        session, "Target", CHASE, t.on(1, 9),
        {"Groceries": "63.10", "Household": "24.50"},
    )
    account_service.make_payment(session, LOAN, _d("285.00"), logged_date=t.on(1, 10))
    _spend(session, "Sushi Palace", CASH, t.on(1, 12), {"Dining Out": "47.80"})
    envelope_service.add_to_cash(
        session, _d("150.00"), "Sold a desk", logged_date=t.on(1, 12)
    )
    account_service.make_payment(session, AMEX, _d("90.00"), logged_date=t.on(1, 13))
    _spend(session, "Verizon", AMEX, t.on(1, 16), {"Phone Bill": "70.00"})

    # --- Cycle 4: paycheck #4 (Sep 18) -------------------------------------------
    envelope_service.add_to_cash(
        session, _d("2400.00"), "Acme Corp Paycheck", logged_date=t.on(1, 18)
    )
    _budget(
        session,
        t.on(1, 18),
        {
            "Groceries": "220", "Gas": "60", "Household": "50", "Dining Out": "60",
            "Skincare": "40", "Entertainment": "40", "Best Buy Laptop - 12": "100",
            "Emergency Fund": "400", "Vacation": "300",
        },
    )
    _spend(session, "Whole Foods", AMEX, t.on(1, 19), {"Groceries": "68.90"})
    _spend(session, "Chevron", CASH, t.on(1, 22), {"Gas": "44.00"})
    _spend(session, "Sunday Brunch Cafe", CASH, t.on(1, 24), {"Dining Out": "38.00"})
    _spend(session, "Sephora", CHASE, t.on(1, 27), {"Skincare": "34.50"})
    account_service.make_payment(session, CHASE, _d("150.00"), logged_date=t.on(1, 30))

    # --- Cycle 5: paycheck #5 (Oct 2) --------------------------------------------
    envelope_service.add_to_cash(
        session, _d("2400.00"), "Acme Corp Paycheck", logged_date=t.on(2, 2)
    )
    _budget(
        session,
        t.on(2, 2),
        {
            "Rent": "1200", "Utilities": "150", "Phone Bill": "70", LOAN: "285",
            "Groceries": "220", "Gas": "60", "Dining Out": "50",
            "Best Buy Laptop - 12": "100", "Emergency Fund": "300", "Vacation": "200",
        },
    )
    envelope_service.transfer_between_envelopes(
        session, "Entertainment", "Skincare", _d("15.00"), logged_date=t.on(2, 3)
    )
    _spend(session, "Landlord", CASH, t.on(2, 5), {"Rent": "1200.00"})
    # The deliberate overspend: a big birthday dinner on the credit card that
    # exceeds what is left in Dining Out.
    _spend(
        session, "Nobu", CHASE, t.on(2, 6), {"Dining Out": "189.60"},
        note="Friend's birthday dinner, went over budget",
    )
    _spend(session, "Shell", CHASE, t.on(2, 8), {"Gas": "41.75"})
    account_service.make_payment(session, LOAN, _d("285.00"), logged_date=t.on(2, 9))

    _verify(session)


def _verify(session: Session) -> None:
    """Asserts the finished story has its intended end state."""
    negatives = {
        env.name
        for env in session.exec(select(Envelope)).all()
        if envelope_repo.get_balance_for_envelope(session, env) < 0
    }
    assert negatives == {OVERSPENT_ENVELOPE}, (
        f"Expected only {OVERSPENT_ENVELOPE!r} to be negative, got {sorted(negatives)}"
    )
    cash = account_service.get_account_balance(session, CASH)
    assert cash > 0, f"Cash should be positive, got {cash}"
    loan = account_service.get_account_balance(session, LOAN)
    assert loan == EXPECTED_LOAN_BALANCE, f"Loan balance {loan} != {EXPECTED_LOAN_BALANCE}"
