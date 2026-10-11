"""Lifecycle helpers for the isolated frontend development databases.

Two databases live on the same Postgres server:

* ``<name>``       -- the live database the dev API serves.
* ``<name>_seed``  -- a pristine seeded copy, used only as a ``TEMPLATE``.

Resetting is "drop the live database and recreate it from the seed template".
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

LIVE_SUFFIX = "_frontend"
SEED_SUFFIX = "_seed"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class UnsafeDevDatabaseError(RuntimeError):
    """Raised when the dev database configuration could touch a non-dev database."""


@dataclass(frozen=True)
class DevDatabaseConfig:
    """Validated names and URLs for the live and seed development databases."""

    live_url: URL

    @property
    def live_name(self) -> str:
        return str(self.live_url.database)

    @property
    def seed_name(self) -> str:
        return f"{self.live_name}{SEED_SUFFIX}"

    @classmethod
    def from_database_url(
        cls, database_url: str | URL, forbidden_names: tuple[str, ...] = ()
    ) -> "DevDatabaseConfig":
        """Builds a config, refusing anything that does not look like a local dev DB.

        Args:
            database_url: URL of the *live* dev database.
            forbidden_names: Database names (e.g. test / prod) that must never be used.

        Raises:
            UnsafeDevDatabaseError: If the host is not local, the name does not end in
                ``_frontend``, or the name is in ``forbidden_names``.
        """
        url = make_url(database_url)
        if not url.database:
            raise UnsafeDevDatabaseError("Dev DATABASE_URL has no database name")
        if url.host not in LOCAL_HOSTS:
            raise UnsafeDevDatabaseError(
                f"Refusing to run dev mode against non-local host {url.host!r}"
            )
        if not url.database.endswith(LIVE_SUFFIX):
            raise UnsafeDevDatabaseError(
                f"Dev database name {url.database!r} must end with {LIVE_SUFFIX!r}"
            )
        if url.database in forbidden_names:
            raise UnsafeDevDatabaseError(
                f"Dev database {url.database!r} collides with a protected database"
            )
        return cls(live_url=url)


def _admin_engine(config: DevDatabaseConfig):
    """Engine connected to the maintenance DB, in autocommit mode (needed for CREATE/DROP DATABASE)."""
    return create_engine(
        config.live_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )


def _quote(engine, name: str) -> str:
    return engine.dialect.identifier_preparer.quote(name)


def drop_database(config: DevDatabaseConfig, name: str) -> None:
    """Drops a database, terminating any open connections to it."""
    admin = _admin_engine(config)
    try:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {_quote(admin, name)} WITH (FORCE)"))
    finally:
        admin.dispose()


def create_database(
    config: DevDatabaseConfig, name: str, template: str | None = None
) -> None:
    """Creates a database, optionally cloned from a template database."""
    admin = _admin_engine(config)
    try:
        with admin.connect() as conn:
            sql = f"CREATE DATABASE {_quote(admin, name)}"
            if template:
                sql += f" TEMPLATE {_quote(admin, template)}"
            conn.execute(text(sql))
    finally:
        admin.dispose()


def drop_all(config: DevDatabaseConfig) -> None:
    """Removes both the live and seed databases (idempotent)."""
    drop_database(config, config.live_name)
    drop_database(config, config.seed_name)


def reset_from_seed(config: DevDatabaseConfig) -> None:
    """Replaces the live database with a fresh copy of the seeded template."""
    drop_database(config, config.live_name)
    create_database(config, config.live_name, template=config.seed_name)
