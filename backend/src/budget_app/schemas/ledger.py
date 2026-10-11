"""Backward-compatible aliases for envelope split schemas."""

from budget_app.schemas.envelope_split import (
    EnvelopeSplitBase,
    EnvelopeSplitRequest,
    EnvelopeSplitResponse,
)

LedgerBase = EnvelopeSplitBase
LedgerRequest = EnvelopeSplitRequest
LedgerResponse = EnvelopeSplitResponse

__all__ = ["LedgerBase", "LedgerRequest", "LedgerResponse"]
