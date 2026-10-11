"""Tests for the optional ``logged_date`` parameter on the money-moving services."""

from datetime import date
from decimal import Decimal

from sqlmodel import Session, col, select

from budget_app.models import Transaction
from budget_app.schemas import AccountCreate, AccountType, EnvelopeBase
from budget_app.services import account_service, envelope_service

PAST = date(2026, 3, 14)


def _tx_by_merchant(session: Session, merchant: str) -> list[Transaction]:
    return list(
        session.exec(select(Transaction).where(col(Transaction.merchant) == merchant))
    )


def _fund(session: Session, envelope: str, amount: str) -> None:
    envelope_service.create_envelope(session, EnvelopeBase(name=envelope))
    envelope_service.add_to_cash(session, Decimal(amount), "Seed money")
    envelope_service.assign_to_envelope(session, envelope, Decimal(amount))


def test_add_to_cash_respects_logged_date(session: Session):
    tx = envelope_service.add_to_cash(
        session, Decimal("100.00"), "Dated Paycheck", logged_date=PAST
    )
    assert tx.logged_date == PAST


def test_add_to_cash_defaults_to_today(session: Session):
    tx = envelope_service.add_to_cash(session, Decimal("100.00"), "Undated Paycheck")
    assert tx.logged_date == date.today()


def test_transfer_between_envelopes_respects_logged_date(session: Session):
    _fund(session, "Src Env", "50.00")
    envelope_service.create_envelope(session, EnvelopeBase(name="Dst Env"))

    result = envelope_service.transfer_between_envelopes(
        session, "Src Env", "Dst Env", Decimal("20.00"), logged_date=PAST
    )

    assert result.transfer_transaction.logged_date == PAST


def test_transfer_between_envelopes_defaults_to_today(session: Session):
    _fund(session, "Src Env", "50.00")
    envelope_service.create_envelope(session, EnvelopeBase(name="Dst Env"))

    result = envelope_service.transfer_between_envelopes(
        session, "Src Env", "Dst Env", Decimal("20.00")
    )

    assert result.transfer_transaction.logged_date == date.today()


def test_assign_to_envelope_respects_logged_date(session: Session):
    envelope_service.create_envelope(session, EnvelopeBase(name="Assign Env"))
    envelope_service.add_to_cash(session, Decimal("100.00"), "Seed money")

    result = envelope_service.assign_to_envelope(
        session, "Assign Env", Decimal("40.00"), logged_date=PAST
    )

    assert result.transfer_transaction.logged_date == PAST


def test_make_payment_respects_logged_date(session: Session):
    account_service.create_account(
        session,
        AccountCreate(
            name="Dated Loan",
            account_type=AccountType.LOAN,
            starting_balance=Decimal("500.00"),
        ),
    )
    envelope_service.add_to_cash(session, Decimal("200.00"), "Seed money")
    envelope_service.assign_to_envelope(session, "Dated Loan", Decimal("100.00"))

    txs = account_service.make_payment(
        session, "Dated Loan", Decimal("100.00"), logged_date=PAST
    )

    assert len(txs) == 2
    assert all(tx.logged_date == PAST for tx in txs)


def test_make_payment_defaults_to_today(session: Session):
    account_service.create_account(
        session,
        AccountCreate(
            name="Undated Loan",
            account_type=AccountType.LOAN,
            starting_balance=Decimal("500.00"),
        ),
    )
    envelope_service.add_to_cash(session, Decimal("200.00"), "Seed money")
    envelope_service.assign_to_envelope(session, "Undated Loan", Decimal("100.00"))

    txs = account_service.make_payment(session, "Undated Loan", Decimal("100.00"))

    assert all(tx.logged_date == date.today() for tx in txs)


def test_create_account_starting_balance_respects_logged_date(session: Session):
    account_service.create_account(
        session,
        AccountCreate(
            name="Back Dated Loan",
            account_type=AccountType.LOAN,
            starting_balance=Decimal("1000.00"),
        ),
        logged_date=PAST,
    )

    starting = [
        tx
        for tx in _tx_by_merchant(session, "Starting Balance")
        if tx.account.name == "Back Dated Loan"
    ]
    assert len(starting) == 1
    assert starting[0].logged_date == PAST


def test_create_account_starting_balance_defaults_to_today(session: Session):
    account_service.create_account(
        session,
        AccountCreate(
            name="Today Loan",
            account_type=AccountType.LOAN,
            starting_balance=Decimal("1000.00"),
        ),
    )

    starting = [
        tx
        for tx in _tx_by_merchant(session, "Starting Balance")
        if tx.account.name == "Today Loan"
    ]
    assert starting[0].logged_date == date.today()
