"""Database engine configuration and session provider.

Loads database connection credentials from environment variables and manages
the SQLModel / SQLAlchemy engine instance and session lifecycle.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

# Load environment variables from .env file
load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise LookupError("Cannot find database url in environment variable")

# Global SQLAlchemy/SQLModel engine instance
engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session, None, None]:
    """Yields a database session context and automatically closes it when finished.

    Yields:
        Active SQLModel Session instance bound to the application engine.
    """
    with Session(engine) as session:
        yield session

