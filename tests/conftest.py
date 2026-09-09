import os
import pytest
from typing import Generator
from dotenv import load_dotenv
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine as create_sqla_engine, text
from sqlmodel import Session, create_engine, SQLModel
from fastapi.testclient import TestClient
from budget_app.api.main import app
from budget_app.db import get_session

# load .env.test before any engine initialization, overriding anything that might have loaded before
load_dotenv(".env.test", override=True)

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
    """

    # Step 1
    if not TEST_DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be defined in .env.test")
    
    ensure_test_database_exists(TEST_DATABASE_URL)

    # Step 2
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

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
