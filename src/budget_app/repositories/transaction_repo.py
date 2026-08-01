from sqlmodel import Session

from budget_app.schemas import transaction
from budget_app.models.transaction import Transaction

def create_transaction(session: Session, transaction_info: transaction.TransactionRequest) -> Transaction:
    new_transaction = Transaction.model_validate(transaction_info)

    session.add(new_transaction)
    return new_transaction