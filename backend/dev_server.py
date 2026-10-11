"""Development server: API on an isolated, seeded frontend database.

Usage (normally via ``npm run dev`` in ``frontend/``)::

    cd backend && uv run python dev_server.py

Lifecycle:
  1. Create ``<db>_frontend`` and ``<db>_frontend_seed`` from scratch, migrate,
     run the production ``init_db`` bootstrap, then seed realistic data.
  2. Serve the API with auto-reload (``POST /dev/reset`` restores the seed).
  3. On Ctrl+C / SIGTERM, drop both databases.

This is a top-level script (not inside ``budget_app``) on purpose: importing the
``budget_app`` package creates the DB engine from ``DATABASE_URL``, so the
environment must be configured *before* the first ``budget_app`` import.
The test database is never touched.
"""

import os
import signal
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DEV_DB_NAME = "budget_db_frontend"
HOST = "127.0.0.1"
PORT = 8000


def resolve_live_url() -> str:
    """Live dev DB URL: ``.env.dev`` if present, else test credentials with a dev DB name."""
    dev_url = dotenv_values(BACKEND_DIR / ".env.dev").get("DATABASE_URL")
    if dev_url:
        return dev_url
    test_url = dotenv_values(BACKEND_DIR / ".env.test").get("DATABASE_URL")
    if not test_url:
        sys.exit("Need DATABASE_URL in backend/.env.dev or backend/.env.test")
    return make_url(test_url).set(database=DEFAULT_DEV_DB_NAME).render_as_string(
        hide_password=False
    )


def protected_names() -> tuple[str, ...]:
    """Database names dev mode must never use (test and main databases)."""
    names = []
    for env_file in (".env", ".env.test"):
        url = dotenv_values(BACKEND_DIR / env_file).get("DATABASE_URL")
        if url:
            names.append(make_url(url).database)
    return tuple(n for n in names if n)


def build(config) -> None:
    """Creates, migrates, bootstraps and seeds the dev databases."""
    from alembic import command
    from alembic.config import Config
    from sqlmodel import Session

    from budget_app.db import engine, init_db
    from budget_app.dev import database
    from budget_app.dev.seed import seed

    print(f"[dev] Recreating databases {config.live_name!r} / {config.seed_name!r}")
    database.drop_all(config)
    database.create_database(config, config.live_name)

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    with Session(engine) as session:
        init_db(session)
        seed(session)
    engine.dispose()

    # The template must have no open connections, hence the dispose above.
    database.create_database(config, config.seed_name, template=config.live_name)
    print("[dev] Seeded. Frontend: http://localhost:5173  API: "
          f"http://{HOST}:{PORT}  Reset: POST /dev/reset")


def teardown(config) -> None:
    """Drops both dev databases, leaving nothing behind."""
    from budget_app.dev import database

    print(f"\n[dev] Cleaning up {config.live_name!r} and {config.seed_name!r}")
    try:
        database.drop_all(config)
    except Exception as exc:  # never mask the original shutdown path
        print(f"[dev] Cleanup failed: {exc}. Next start will drop leftovers.")


def main() -> None:
    live_url = resolve_live_url()
    # Must happen before any budget_app import (the engine reads this at import).
    os.environ["DATABASE_URL"] = live_url
    os.environ["APP_ENV"] = "dev"

    from budget_app.dev.database import DevDatabaseConfig, UnsafeDevDatabaseError

    try:
        config = DevDatabaseConfig.from_database_url(live_url, protected_names())
    except UnsafeDevDatabaseError as exc:
        sys.exit(f"[dev] {exc}")

    # Make SIGTERM run the `finally` below, like Ctrl+C does.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    try:
        build(config)

        import uvicorn

        uvicorn.run(
            "budget_app.api.main:app",
            host=HOST,
            port=PORT,
            reload=True,
            reload_dirs=[str(BACKEND_DIR / "src")],
        )
    finally:
        teardown(config)


if __name__ == "__main__":
    main()
