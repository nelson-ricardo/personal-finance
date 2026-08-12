import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise LookupError("Cannot find database url in environment variable")

engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session, None, None]:

    with Session(engine) as session:
        yield session
