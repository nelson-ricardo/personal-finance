from sqlmodel import Session
from budget_app.schemas.transaction import TransactionRequest

def add_transaction(session: Session, new_transaction: TransactionRequest):
    # check if we have a valid envelope and get its id back
    pass