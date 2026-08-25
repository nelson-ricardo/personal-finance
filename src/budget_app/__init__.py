"""Personal Budgeting Application.

A zero-based envelope budgeting system built with SQLModel, SQLAlchemy, and PostgreSQL.
Provides multi-account management (Cash, Credit Card, Loans), envelope allocation,
split expense handling, credit card balancing entries, and financed transaction support.
"""

from budget_app import db, models, repositories, schemas, services
from budget_app.db import engine, get_session, init_db
from budget_app.models import Account, Envelope, Ledger, Transaction
from budget_app.schemas import (
    AccountBase,
    AccountType,
    EnvelopeBase,
    EnvelopeTransfer,
    LedgerBase,
    LedgerRequest,
    LedgerResponse,
    TransactionBase,
    TransactionDetailResponse,
    TransactionRequest,
    TransactionResponse,
    TransactionType,
)
from budget_app.services import (
    add_financed_transaction,
    add_reg_transaction,
    add_to_cash,
    assign_to_envelope,
    create_account,
    create_envelope,
    delete_transaction,
    fetch_transaction_by_id,
    fetch_transactions,
    get_transaction,
    get_transaction_by_id,
    get_transactions,
    reverse_transaction,
    transfer_between_envelopes,
    transfer_from_unassigned,
)


__all__ = [
    # Subpackages
    "models",
    "schemas",
    "repositories",
    "services",
    "db",
    # DB
    "engine",
    "get_session",
    "init_db",
    # Models
    "Account",
    "Envelope",
    "Ledger",
    "Transaction",
    # Schemas
    "AccountType",
    "AccountBase",
    "EnvelopeBase",
    "EnvelopeTransfer",
    "LedgerBase",
    "LedgerRequest",
    "LedgerResponse",
    "TransactionType",
    "TransactionBase",
    "TransactionRequest",
    "TransactionResponse",
    "TransactionDetailResponse",
    # Services
    "create_account",
    "create_envelope",
    "add_to_cash",
    "transfer_between_envelopes",
    "assign_to_envelope",
    "transfer_from_unassigned",
    "add_reg_transaction",
    "add_financed_transaction",
    "get_transactions",
    "get_transaction",
    "fetch_transactions",
    "get_transaction_by_id",
    "fetch_transaction_by_id",
    "delete_transaction",
    "reverse_transaction",
]




