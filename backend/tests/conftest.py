import os
from pathlib import Path
from typing import Generator

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as create_sqla_engine
from sqlalchemy import text
from sqlmodel import Session, create_engine, select

from alembic import command
from budget_app.api.main import app
from budget_app.db import get_session

BASE_DIR = Path(__file__).resolve().parents[1]

# load .env.test before any engine initialization, overriding anything that might have loaded before
load_dotenv(BASE_DIR / ".env.test", override=True)
os.environ.pop("APP_ENV", None)

TEST_DATABASE_URL = os.getenv("DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be defined in .env.test")

def ensure_test_database_exists(db_url: str) -> None:
    """
    Connect to default PostgreSQL server to ensure the test database
    specified in TEST_DATABASE_URL exists. Creates if missing
    """
    base_url, db_name = db_url.rsplit("/", 1)
    admin_url = f"{base_url}/postgres"

    admin_engine = create_sqla_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": db_name}
        )
        if not result.scalar():
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"\nCreated test database: {db_name}")

    admin_engine.dispose()

@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """
    Session-wide setup:
    1. Ensures the test database exists in the PostgreSQL server
    2. Runs 'alembic upgrade head' to apply all migrations
    3. Runs init_db to seed initial system records if missing
    """

    # Step 1
    if not TEST_DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be defined in .env.test")
    
    ensure_test_database_exists(TEST_DATABASE_URL)

    # Step 2
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    # Step 3: Ensure base system category, system envelopes, and cash account exist
    from decimal import Decimal

    from budget_app.models import Envelope, EnvelopeCategory
    from budget_app.repositories import account_repo
    from budget_app.schemas import AccountCreate, AccountType, SystemEnvelopeType

    init_engine = create_engine(TEST_DATABASE_URL)
    with Session(init_engine) as init_session:
        system_cat = init_session.exec(
            select(EnvelopeCategory).where(EnvelopeCategory.name == "System")
        ).first()
        if not system_cat:
            system_cat = EnvelopeCategory(name="System", order_index=99, is_active=True)
            init_session.add(system_cat)
            init_session.commit()
            init_session.refresh(system_cat)

        system_envelopes = [
            ("Unassigned", SystemEnvelopeType.UNASSIGNED, "default bucket for money coming in"),
            ("Credit Card Payment", SystemEnvelopeType.CREDIT_CARD_PAYMENT, "holding envelope for credit card balance payoffs"),
            ("Account Adjustment", SystemEnvelopeType.ACCOUNT_ADJUSTMENT, "system envelope absorbing debt for account balance adjustments"),
        ]
        for name, role, note in system_envelopes:
            existing = init_session.exec(
                select(Envelope).where((Envelope.system_role == role) | (Envelope.name == name))
            ).first()
            if not existing:
                init_session.add(
                    Envelope(
                        name=name,
                        system_role=role,
                        note=note,
                        category_id=system_cat.id,
                        is_active=True,
                    )
                )
            elif existing.system_role != role:
                existing.system_role = role
                init_session.add(existing)

        cash = account_repo.get_account_by_name(init_session, "Cash")
        if not cash:
            account_repo.create_account(
                init_session,
                AccountCreate(
                    name="Cash",
                    account_type=AccountType.CASH,
                    starting_balance=Decimal("0.00"),
                ),
            )

        init_session.commit()
    init_engine.dispose()

    yield

@pytest.fixture(scope="session")
def db_engine():
    """
    create a single SQLModel engine for the test session
    """
    if not TEST_DATABASE_URL:
            raise RuntimeError("DATABASE_URL must be defined in .env.test")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def session(db_engine) -> Generator[Session, None, None]:
    """
    Main fixture

    Creates an outer SQL Transaction for every test function. All commits/adds
    inside of the test will run under this transaction. When the test ends,
    the entire transaction is rolled back.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection)

    yield session

    # Teardown portion, rollback the transaction and close the connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(session: Session) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides to use the per-test database session."""
    def _get_test_session():
        yield session

    app.dependency_overrides[get_session] = _get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
