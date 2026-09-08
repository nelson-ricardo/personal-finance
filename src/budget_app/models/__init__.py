"""Database ORM models package.

Defines SQLModel database entities:
- Account: Financial accounts (Cash, Credit Card, Loans).
- Envelope: Budgeting category buckets.
- Ledger: Individual transaction splits allocated to envelopes.
- Transaction: Master financial transaction record.
"""

from budget_app.models.account import Account
from budget_app.models.category import EnvelopeCategory
from budget_app.models.envelope import Envelope
from budget_app.models.envelope_split import EnvelopeSplit
from budget_app.models.ledger import Ledger
from budget_app.models.transaction import Transaction
from budget_app.schemas import EnvelopeTransfer

# Rebuild forward references for schemas referencing models
EnvelopeTransfer.model_rebuild()

__all__ = ["Account", "Envelope", "EnvelopeCategory", "EnvelopeSplit", "Ledger", "Transaction"]


