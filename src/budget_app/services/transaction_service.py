from decimal import Decimal

from sqlmodel import Session

from budget_app.models import Account, Transaction
from budget_app.repositories import (
    account_repo,
    ledger_repo,
    transaction_repo,
)
from budget_app.schemas import AccountType, LedgerRequest, TransactionRequest


def add_reg_transaction(session: Session, transaction: TransactionRequest) -> Transaction:
    """
    Adds a regular transaction and adds the corresponding entries.
    If a credit card was used it will add the total to the 'credit card payment'
    envelope.\n
    session: object holding the database session
    transaction: TransactionRequest
    """

    payment_method: Account | None = account_repo.get_account_by_name(
        session, transaction.payment_method_name
    )

    if not payment_method:
        raise ValueError(f"Account {transaction.payment_method_name} does not exist")

    # getting transaction total to add to cc payment or deduct from cash balance
    transaction_total = Decimal("0")
    for entry in transaction.ledger_entries:
        transaction_total += abs(entry.amount)

    master_transaction: Transaction = transaction_repo.create_transaction(session, transaction)

    # move money to credit card payment to balance the transaction out
    # or remove money from cash account if it is a cash payment
    if payment_method.account_type is AccountType.CREDIT_CARD:
        cc_payment = ledger_repo.add_ledger_entry(
            session, 
            LedgerRequest(amount=transaction_total, envelope_name="Credit Card Payment")
        )
        master_transaction.entries.append(cc_payment)
        payment_method.current_balance += transaction_total
    if payment_method.account_type is AccountType.CASH:
        payment_method.current_balance -= transaction_total

    session.add(payment_method)
    session.commit()
    session.refresh(master_transaction)
    return master_transaction

def add_financed_transaction(session: Session, transaction: TransactionRequest):
    pass
