"""Main application entry point.

Run the production API::

    uv run python main.py

Run in development mode (spawns isolated frontend database, seeds data, enables CORS & /dev/reset)::

    uv run python main.py --dev
"""

import argparse
import os
import signal
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DEV_DB_NAME = "budget_db_frontend"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))


def resolve_dev_url() -> str:
    """Live dev DB URL: DATABASE_URL if set, else ``.env.dev``, else test credentials."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    dev_url = dotenv_values(BACKEND_DIR / ".env.dev").get("DATABASE_URL")
    if dev_url:
        return dev_url
    test_url = dotenv_values(BACKEND_DIR / ".env.test").get("DATABASE_URL")
    if not test_url:
        sys.exit("Need DATABASE_URL in environment, backend/.env.dev or backend/.env.test")
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


def build_dev_db(config) -> None:
    """Creates, migrates, bootstraps and seeds the dev databases."""
    from alembic import command
    from alembic.config import Config
    from sqlmodel import Session

    from budget_app.db import (
        database,
        engine,
        init_db,
        seed,
    )

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
    print(
        f"[dev] Seeded. Frontend: http://localhost:5173  API: http://{HOST}:{PORT}  Reset: POST /dev/reset"
    )


def teardown_dev_db(config) -> None:
    """Drops both dev databases, leaving nothing behind."""
    from budget_app.db import database

    print(f"\n[dev] Cleaning up {config.live_name!r} and {config.seed_name!r}")
    try:
        database.drop_all(config)
    except Exception as exc:  # never mask the original shutdown path
        print(f"[dev] Cleanup failed: {exc}. Next start will drop leftovers.")


def run_dev():
    """Runs the server in development mode."""
    live_url = resolve_dev_url()
    # Must happen before any budget_app import (engine reads this at import)
    os.environ["DATABASE_URL"] = live_url
    os.environ["APP_ENV"] = "dev"

    from budget_app.db.database import DevDatabaseConfig, UnsafeDevDatabaseError

    is_legacy_local = False
    try:
        config = DevDatabaseConfig.from_database_url(live_url, protected_names())
        is_legacy_local = True
    except UnsafeDevDatabaseError:
        pass

    if is_legacy_local:
        # Make SIGTERM run the finally cleanup below, just like Ctrl+C does
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        try:
            build_dev_db(config)

            import uvicorn

            uvicorn.run(
                "budget_app.api.main:app",
                host=HOST,
                port=PORT,
                reload=True,
                reload_dirs=[str(BACKEND_DIR / "src")],
            )
        finally:
            teardown_dev_db(config)
    else:
        # Running in Docker or standard containerized dev environment
        from alembic import command
        from alembic.config import Config
        from sqlmodel import Session, select

        from budget_app.db import engine
        from budget_app.models import Account
        from budget_app.services import checkpoint_service

        try:
            command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
        except Exception as e:
            print(f"[dev] Migration note: {e}")

        try:
            with Session(engine) as session:
                has_accounts = session.exec(select(Account)).first() is not None
                if not has_accounts:
                    print("[dev] Fresh dev database detected. Restoring 'alex_seed'...")
                    checkpoint_service.restore_checkpoint(session, "alex_seed")
        except Exception as e:
            print(f"[dev] Initial seed note: {e}")

        import uvicorn

        uvicorn.run(
            "budget_app.api.main:app",
            host=HOST,
            port=PORT,
            reload=True,
            reload_dirs=[str(BACKEND_DIR / "src")],
        )


def run_prod():
    """Runs the server in standard/production mode using DATABASE_URL from environment."""
    os.environ["APP_ENV"] = "prod"

    from alembic import command
    from alembic.config import Config
    from sqlmodel import Session, select

    from budget_app.db import engine
    from budget_app.models import Account
    from budget_app.services import checkpoint_service

    try:
        command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    except Exception as e:
        print(f"[prod] Migration note: {e}")

    try:
        with Session(engine) as session:
            has_accounts = session.exec(select(Account)).first() is not None
            if not has_accounts:
                print("[prod] Clean database detected. Bootstrapping 'clean_slate' baseline...")
                checkpoint_service.restore_checkpoint(session, "clean_slate")
    except Exception as e:
        print(f"[prod] Bootstrap note: {e}")

    import uvicorn

    uvicorn.run(
        "budget_app.api.main:app",
        host=HOST,
        port=PORT,
        reload=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Personal Budgeting API Server")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with isolated frontend testing database and sample seed data",
    )
    args = parser.parse_args()

    # Also respect APP_ENV=dev if passed via environment variable
    if args.dev or os.getenv("APP_ENV") == "dev":
        run_dev()
    else:
        run_prod()


if __name__ == "__main__":
    main()
