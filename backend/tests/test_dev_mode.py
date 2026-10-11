"""Tests for the frontend dev mode: timeline, seed story, DB lifecycle and reset route."""

import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from budget_app.api.routes import dev as dev_routes
from budget_app.db import (
    DevDatabaseConfig,
    Timeline,
    UnsafeDevDatabaseError,
    anchor_for,
    database,
    init_db,
    seed,
)
from budget_app.models import Envelope, EnvelopeSplit, Transaction
from budget_app.repositories import envelope_repo
from budget_app.services import account_service

TODAY = date(2026, 10, 11)


# --- Timeline ---------------------------------------------------------------


@pytest.mark.parametrize(
    "today, expected",
    [
        (date(2026, 10, 11), date(2026, 8, 1)),
        (date(2027, 1, 3), date(2026, 11, 1)),
        (date(2027, 2, 28), date(2026, 12, 1)),
        (date(2026, 3, 31), date(2026, 1, 1)),
    ],
)
def test_anchor_is_first_of_month_two_months_back(today, expected):
    assert anchor_for(today) == expected


def test_timeline_resolves_calendar_dates():
    t = Timeline(TODAY)
    assert t.on(0, 7) == date(2026, 8, 7)
    assert t.on(1, 18) == date(2026, 9, 18)
    assert t.on(2, 6) == date(2026, 10, 6)


def test_timeline_never_returns_future_dates():
    t = Timeline(date(2026, 10, 3))
    assert t.on(2, 9) == date(2026, 10, 3)


def test_timeline_clamps_days_past_month_end():
    t = Timeline(date(2026, 12, 20))  # anchor Oct 1; month+1 = Nov (30 days)
    assert t.on(1, 31) == date(2026, 11, 30)


def test_next_day_of_month_is_strictly_in_the_future():
    t = Timeline(date(2026, 12, 25))
    assert t.next_day_of_month(25) == date(2027, 1, 25)
    assert t.next_day_of_month(26) == date(2026, 12, 26)


# --- Seed -------------------------------------------------------------------


def _seeded(session: Session, today: date = TODAY) -> None:
    init_db(session)
    seed(session, today=today)


def test_seed_builds_the_expected_story(session: Session):
    _seeded(session)

    accounts = {a.name: a for a in account_service.get_all_accounts(session)}
    assert {"Cash", "Chase Sapphire", "Amex Blue", "Honda Civic Loan"} <= set(accounts)
    assert account_service.get_account_balance(session, "Honda Civic Loan") == Decimal(
        "7545.00"
    )
    assert account_service.get_account_balance(session, "Cash") > 0

    names = {e.name for e in session.exec(select(Envelope)).all()}
    assert {"Unassigned", "Credit Card Payment", "Account Adjustment"} <= names
    assert "Best Buy Laptop - 12" in names

    transactions = session.exec(select(Transaction)).all()
    assert len(transactions) >= 60
    assert min(tx.logged_date for tx in transactions) == date(2026, 8, 1)
    assert max(tx.logged_date for tx in transactions) <= TODAY


def test_seed_has_multi_envelope_transactions(session: Session):
    _seeded(session)

    target_on_chase = [
        tx
        for tx in session.exec(select(Transaction)).all()
        if tx.merchant == "Target" and tx.account.name == "Chase Sapphire"
    ]
    assert target_on_chase
    spent_splits = [
        [s for s in tx.splits if s.amount < 0] for tx in target_on_chase
    ]
    assert any(len(s) == 3 for s in spent_splits)


def test_seed_leaves_only_dining_out_negative(session: Session):
    _seeded(session)

    balances = {
        e.name: envelope_repo.get_balance_for_envelope(session, e)
        for e in session.exec(select(Envelope)).all()
    }
    assert [name for name, bal in balances.items() if bal < 0] == ["Dining Out"]


@pytest.mark.parametrize(
    "today",
    [date(2026, 10, 2), date(2027, 1, 1), date(2026, 3, 31), date(2028, 3, 1)],
)
def test_seed_works_for_any_run_date_without_future_transactions(
    session: Session, today: date
):
    _seeded(session, today=today)

    latest = max(tx.logged_date for tx in session.exec(select(Transaction)).all())
    assert latest <= today


# --- Database lifecycle & guards --------------------------------------------


def _test_url():
    return make_url(os.environ["DATABASE_URL"])


def test_guard_rejects_non_local_host():
    url = _test_url().set(host="db.example.com", database="x_frontend")
    with pytest.raises(UnsafeDevDatabaseError):
        DevDatabaseConfig.from_database_url(url)


def test_guard_rejects_non_frontend_name():
    with pytest.raises(UnsafeDevDatabaseError):
        DevDatabaseConfig.from_database_url(_test_url().set(host="localhost"))


def test_guard_rejects_protected_name():
    url = _test_url().set(host="localhost", database="protected_frontend")
    with pytest.raises(UnsafeDevDatabaseError):
        DevDatabaseConfig.from_database_url(url, forbidden_names=("protected_frontend",))


@pytest.fixture
def throwaway_config():
    url = _test_url().set(host="localhost", database="budget_db_pytest_frontend")
    config = DevDatabaseConfig.from_database_url(url)
    database.drop_all(config)
    yield config
    database.drop_all(config)


def _scalar(config: DevDatabaseConfig, sql: str, db: str | None = None):
    engine = create_engine(config.live_url.set(database=db or config.live_name))
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def _exec(config: DevDatabaseConfig, sql: str) -> None:
    engine = create_engine(config.live_url)
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
    finally:
        engine.dispose()


def test_reset_restores_seeded_state_and_drop_all_cleans_up(throwaway_config):
    config = throwaway_config
    database.create_database(config, config.live_name)
    _exec(config, "CREATE TABLE things (id serial primary key, label text)")
    _exec(config, "INSERT INTO things (label) VALUES ('seeded-1'), ('seeded-2')")
    database.create_database(config, config.seed_name, template=config.live_name)

    # Simulated frontend activity: insert, update, delete.
    _exec(config, "INSERT INTO things (label) VALUES ('frontend-added')")
    _exec(config, "UPDATE things SET label = 'changed' WHERE label = 'seeded-1'")
    _exec(config, "DELETE FROM things WHERE label = 'seeded-2'")
    assert _scalar(config, "SELECT count(*) FROM things WHERE label LIKE 'seeded%'") == 0

    database.reset_from_seed(config)

    assert _scalar(config, "SELECT count(*) FROM things") == 2
    assert _scalar(config, "SELECT count(*) FROM things WHERE label LIKE 'seeded-%'") == 2
    # sequences carry over too: the next id continues after the seeded rows
    _exec(config, "INSERT INTO things (label) VALUES ('after-reset')")
    assert _scalar(config, "SELECT max(id) FROM things") == 3

    database.drop_all(config)
    existing = _scalar(
        config,
        "SELECT count(*) FROM pg_database WHERE datname LIKE 'budget_db_pytest_frontend%'",
        db="postgres",
    )
    assert existing == 0


# --- Reset route ------------------------------------------------------------


def test_reset_route_is_not_mounted_outside_dev_mode(client: TestClient):
    assert client.post("/dev/reset").status_code == 404


def test_reset_route_runs_reset_and_reports_status(monkeypatch):
    calls = []
    monkeypatch.setattr(dev_routes, "_reset", lambda: calls.append("reset"))
    app = FastAPI()
    app.include_router(dev_routes.router)

    response = TestClient(app).post("/dev/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert calls == ["reset"]
