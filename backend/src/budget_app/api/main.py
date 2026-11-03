import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from budget_app.api.routes import (
    accounts,
    categories,
    envelopes,
    notifications,
    obligations,
    transactions,
)
from budget_app.db.engine import engine
from budget_app.services import notification_service

logger = logging.getLogger(__name__)


async def reminder_scheduler_loop():
    """Background worker that ticks every 60 seconds to check and dispatch scheduled reminders."""
    logger.info("Daily obligation reminder scheduler initialized.")
    while True:
        try:
            with Session(engine) as session:
                notification_service.check_and_dispatch_due_reminders(session, force=False)
        except Exception as e:
            logger.debug(f"Reminder scheduler tick exception: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(reminder_scheduler_loop())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Personal Finance API", lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(envelopes.router)
app.include_router(transactions.router)
app.include_router(notifications.router)
app.include_router(obligations.router)

@app.get("/health")
async def health():
    return {
        "message": "Up and Running!"
    }


# Development and UAT wiring. Enabled in dev or prod (APP_ENV in ("dev", "prod")).
# Hidden routes /dev/checkpoints allow database snapshots and safe rollback.
if os.getenv("APP_ENV") in ("dev", "prod"):
    from fastapi.middleware.cors import CORSMiddleware

    from budget_app.api.routes import dev

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(dev.router)