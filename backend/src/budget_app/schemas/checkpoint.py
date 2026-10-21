"""Schemas for developer checkpoints and database snapshots."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckpointStats(BaseModel):
    """Summary metrics of the database state at the time of the checkpoint."""

    accounts_count: int = Field(default=0, description="Total number of accounts")
    categories_count: int = Field(default=0, description="Total number of envelope categories")
    envelopes_count: int = Field(default=0, description="Total number of envelopes")
    transactions_count: int = Field(default=0, description="Total number of master transactions")
    total_cash: Decimal = Field(default=Decimal("0.00"), description="Sum of liquid cash account balances")
    total_debt: Decimal = Field(default=Decimal("0.00"), description="Sum of credit card and loan debt balances")


class CheckpointSummary(BaseModel):
    """Metadata summary of a saved database checkpoint."""

    id: str = Field(description="Unique checkpoint identifier / filename prefix")
    name: str = Field(description="User-provided label or default display title")
    filename: str = Field(description="File name of the dump file on the server")
    created_at: str = Field(description="ISO-8601 formatted timestamp of creation")
    size_bytes: int = Field(default=0, description="File size on disk in bytes")
    stats: CheckpointStats = Field(description="Summary counts and financial balances")


class CheckpointCreateRequest(BaseModel):
    """Request payload for creating a new database checkpoint."""

    name: Optional[str] = Field(default=None, description="Optional custom label for the checkpoint")


class CheckpointRestoreResponse(BaseModel):
    """Response payload when a database checkpoint is successfully restored."""

    status: str = Field(default="restored")
    message: str = Field(description="Human-readable success confirmation")
    checkpoint: CheckpointSummary = Field(description="The checkpoint that was restored")
