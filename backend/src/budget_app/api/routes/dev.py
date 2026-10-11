"""Development-only endpoints. Mounted by ``api/main.py`` only when ``APP_ENV=dev``."""

import asyncio
import os

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from budget_app.db import engine
from budget_app.dev import database
from budget_app.dev.database import DevDatabaseConfig

router = APIRouter(prefix="/dev", tags=["dev"])

# Serialises resets so two concurrent calls cannot race on DROP/CREATE DATABASE.
_reset_lock = asyncio.Lock()


def _reset() -> None:
    config = DevDatabaseConfig.from_database_url(os.environ["DATABASE_URL"])
    # Drop pooled connections first; DROP DATABASE ... WITH (FORCE) kills any in flight.
    engine.dispose()
    database.reset_from_seed(config)
    engine.dispose()


@router.post("/reset")
async def reset_database() -> dict[str, str]:
    """Rolls the frontend database back to the freshly seeded state."""
    async with _reset_lock:
        await run_in_threadpool(_reset)
    return {"status": "reset"}
