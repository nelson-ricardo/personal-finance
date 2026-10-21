"""Service for managing point-in-time database snapshots and checkpoints."""

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from sqlmodel import Session, delete, select, text

from budget_app.models import Account, Envelope, EnvelopeCategory, EnvelopeSplit, Transaction
from budget_app.repositories import account_repo
from budget_app.schemas import AccountType
from budget_app.schemas.checkpoint import CheckpointStats, CheckpointSummary


def get_checkpoints_dir() -> Path:
    """Returns the directory used for storing checkpoint snapshots, ensuring it exists."""
    env_dir = os.getenv("CHECKPOINTS_DIR")
    if env_dir:
        path = Path(env_dir)
    else:
        # Default to checkpoints/ in the project root
        path = Path(__file__).resolve().parents[4] / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_slug(text: str) -> str:
    """Sanitizes text to safe alphanumeric characters and dashes."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")
    return cleaned[:30] if cleaned else "snapshot"


def _dump_table(session: Session, model_cls: Any) -> List[Dict[str, Any]]:
    """Dumps all rows of a model, filtering strictly to database table columns."""
    columns = set(model_cls.__table__.columns.keys())
    rows = session.exec(select(model_cls)).all()
    results: List[Dict[str, Any]] = []
    for row in rows:
        dumped = row.model_dump(mode="json")
        filtered = {k: v for k, v in dumped.items() if k in columns}
        results.append(filtered)
    return results


def list_checkpoints() -> List[CheckpointSummary]:
    """Lists all available database checkpoint dumps, sorted by newest first."""
    checkpoints_dir = get_checkpoints_dir()
    summaries: List[CheckpointSummary] = []

    for file_path in checkpoints_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stats_data = data.get("stats", {})
            stats = CheckpointStats(
                accounts_count=stats_data.get("accounts_count", 0),
                categories_count=stats_data.get("categories_count", 0),
                envelopes_count=stats_data.get("envelopes_count", 0),
                transactions_count=stats_data.get("transactions_count", 0),
                total_cash=Decimal(str(stats_data.get("total_cash", "0.00"))),
                total_debt=Decimal(str(stats_data.get("total_debt", "0.00"))),
            )

            summaries.append(
                CheckpointSummary(
                    id=data.get("id", file_path.stem),
                    name=data.get("name", file_path.stem),
                    filename=file_path.name,
                    created_at=data.get("created_at", ""),
                    size_bytes=file_path.stat().st_size,
                    stats=stats,
                )
            )
        except Exception:
            # Skip invalid or corrupt JSON files gracefully
            continue

    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def create_checkpoint(session: Session, name: Optional[str] = None) -> CheckpointSummary:
    """Takes a complete snapshot of all database tables and writes it to disk."""
    checkpoints_dir = get_checkpoints_dir()
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")

    label = name.strip() if name and name.strip() else f"Snapshot {now.strftime('%b %d, %Y %I:%M %p')}"
    slug = _sanitize_slug(label)
    checkpoint_id = f"dump_{timestamp_str}_{slug}"
    filename = f"{checkpoint_id}.json"
    file_path = checkpoints_dir / filename

    # Compute financial balances
    accounts = session.exec(select(Account)).all()
    total_cash = Decimal("0.00")
    total_debt = Decimal("0.00")
    for acc in accounts:
        bal = account_repo.get_balance_for_account(session, acc)
        if acc.account_type == AccountType.CASH:
            total_cash += bal
        else:
            total_debt += bal

    # Export all tables
    categories_data = _dump_table(session, EnvelopeCategory)
    envelopes_data = _dump_table(session, Envelope)
    accounts_data = _dump_table(session, Account)
    transactions_data = _dump_table(session, Transaction)
    splits_data = _dump_table(session, EnvelopeSplit)

    stats = CheckpointStats(
        accounts_count=len(accounts_data),
        categories_count=len(categories_data),
        envelopes_count=len(envelopes_data),
        transactions_count=len(transactions_data),
        total_cash=total_cash,
        total_debt=total_debt,
    )

    payload = {
        "version": "1.0",
        "id": checkpoint_id,
        "name": label,
        "filename": filename,
        "created_at": now.isoformat(),
        "stats": {
            "accounts_count": stats.accounts_count,
            "categories_count": stats.categories_count,
            "envelopes_count": stats.envelopes_count,
            "transactions_count": stats.transactions_count,
            "total_cash": str(stats.total_cash),
            "total_debt": str(stats.total_debt),
        },
        "data": {
            "envelope_category": categories_data,
            "envelope": envelopes_data,
            "account": accounts_data,
            "transaction": transactions_data,
            "envelope_split": splits_data,
        },
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return CheckpointSummary(
        id=checkpoint_id,
        name=label,
        filename=filename,
        created_at=now.isoformat(),
        size_bytes=file_path.stat().st_size,
        stats=stats,
    )


def restore_checkpoint(session: Session, checkpoint_id: str) -> CheckpointSummary:
    """Restores the database state from a saved checkpoint dump."""
    checkpoints_dir = get_checkpoints_dir()
    file_path = checkpoints_dir / f"{checkpoint_id}.json"
    if not file_path.exists():
        raise ValueError(f"Checkpoint dump '{checkpoint_id}' does not exist on the server")

    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload.get("data", {})

    # 1. Clear existing data in reverse topological order (children before parents)
    session.exec(delete(EnvelopeSplit))
    session.exec(delete(Transaction))
    session.exec(delete(Account))
    session.exec(delete(Envelope))
    session.exec(delete(EnvelopeCategory))
    session.flush()

    # 2. Re-insert data in topological order (parents before children)
    for row in data.get("envelope_category", []):
        session.add(EnvelopeCategory.model_validate(row))
    session.flush()

    for row in data.get("envelope", []):
        session.add(Envelope.model_validate(row))
    session.flush()

    for row in data.get("account", []):
        session.add(Account.model_validate(row))
    session.flush()

    for row in data.get("transaction", []):
        session.add(Transaction.model_validate(row))
    session.flush()

    for row in data.get("envelope_split", []):
        session.add(EnvelopeSplit.model_validate(row))
    session.flush()

    # 3. If running against PostgreSQL, reset auto-increment ID sequences to avoid PK collisions
    if session.bind and session.bind.dialect.name == "postgresql":
        table_cols = [
            ("envelope_category", "id"),
            ("envelope", "id"),
            ("account", "id"),
            ("transaction", "id"),
            ("envelope_split", "id"),
        ]
        for tbl, col in table_cols:
            quoted_tbl = f'"{tbl}"' if tbl == "transaction" else tbl
            session.exec(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{quoted_tbl}', '{col}'), COALESCE(MAX({col}), 1), MAX({col}) IS NOT NULL) FROM {quoted_tbl};"
                )
            )

    session.commit()

    stats_data = payload.get("stats", {})
    stats = CheckpointStats(
        accounts_count=stats_data.get("accounts_count", 0),
        categories_count=stats_data.get("categories_count", 0),
        envelopes_count=stats_data.get("envelopes_count", 0),
        transactions_count=stats_data.get("transactions_count", 0),
        total_cash=Decimal(str(stats_data.get("total_cash", "0.00"))),
        total_debt=Decimal(str(stats_data.get("total_debt", "0.00"))),
    )

    return CheckpointSummary(
        id=payload.get("id", checkpoint_id),
        name=payload.get("name", checkpoint_id),
        filename=file_path.name,
        created_at=payload.get("created_at", ""),
        size_bytes=file_path.stat().st_size,
        stats=stats,
    )


def delete_checkpoint(checkpoint_id: str) -> bool:
    """Deletes a checkpoint dump file from the server."""
    checkpoints_dir = get_checkpoints_dir()
    file_path = checkpoints_dir / f"{checkpoint_id}.json"
    if not file_path.exists():
        raise ValueError(f"Checkpoint dump '{checkpoint_id}' does not exist on the server")
    file_path.unlink()
    return True
