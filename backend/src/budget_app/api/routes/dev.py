"""Development and UAT endpoints. Mounted when APP_ENV=dev."""

import asyncio
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from budget_app.db import database, engine, get_session
from budget_app.db.database import DevDatabaseConfig
from budget_app.schemas.checkpoint import (
    CheckpointCreateRequest,
    CheckpointRestoreResponse,
    CheckpointSummary,
)
from budget_app.services import checkpoint_service

router = APIRouter(prefix="/dev", tags=["dev"])

# Serialises resets so two concurrent calls cannot race on DROP/CREATE DATABASE.
_reset_lock = asyncio.Lock()


def _reset() -> None:
    try:
        config = DevDatabaseConfig.from_database_url(os.environ["DATABASE_URL"])
        # Drop pooled connections first; DROP DATABASE ... WITH (FORCE) kills any in flight.
        engine.dispose()
        database.reset_from_seed(config)
        engine.dispose()
    except Exception:
        # Fallback to restoring alex_seed checkpoint if DevDatabaseConfig is not active
        with Session(engine) as session:
            checkpoint_service.restore_checkpoint(session, "alex_seed")


@router.post("/reset")
async def reset_database() -> dict[str, str]:
    """Rolls the frontend database back to the freshly seeded state."""
    try:
        async with _reset_lock:
            await run_in_threadpool(_reset)
        return {"status": "reset"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/checkpoints", response_model=List[CheckpointSummary], status_code=status.HTTP_200_OK)
def list_checkpoints():
    """Lists all saved database checkpoint snapshots on the server."""
    return checkpoint_service.list_checkpoints()


@router.post("/checkpoints", response_model=CheckpointSummary, status_code=status.HTTP_201_CREATED)
def create_checkpoint(
    payload: Optional[CheckpointCreateRequest] = None,
    session: Session = Depends(get_session),
):
    """Creates a new point-in-time database snapshot dump."""
    try:
        name = payload.name if payload else None
        return checkpoint_service.create_checkpoint(session=session, name=name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/checkpoints/{checkpoint_id}/restore",
    response_model=CheckpointRestoreResponse,
    status_code=status.HTTP_200_OK,
)
def restore_checkpoint(
    checkpoint_id: str,
    session: Session = Depends(get_session),
):
    """Restores the database state from a specified checkpoint dump."""
    try:
        restored = checkpoint_service.restore_checkpoint(session=session, checkpoint_id=checkpoint_id)
        return CheckpointRestoreResponse(
            status="restored",
            message=f"Database successfully restored to checkpoint '{restored.name}'!",
            checkpoint=restored,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/checkpoints/{checkpoint_id}", status_code=status.HTTP_200_OK)
def delete_checkpoint(checkpoint_id: str):
    """Deletes a checkpoint snapshot file from the server."""
    try:
        checkpoint_service.delete_checkpoint(checkpoint_id=checkpoint_id)
        return {"status": "deleted", "message": f"Checkpoint '{checkpoint_id}' deleted."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
