"""Backward-compatible aliases for envelope_split_repo."""

from budget_app.repositories.envelope_split_repo import (
    add_envelope_split,
    add_ledger_entry,
)

__all__ = ["add_envelope_split", "add_ledger_entry"]
