from decimal import Decimal

from sqlmodel import Session

from budget_app.schemas.transaction import TransactionRequest
from budget_app.models.account import Account
from budget_app.schemas.account import AccountType
from budget_app.repositories import account_repo, envelope_repo, transaction_repo, ledger_repo


def add_reg_transaction(session: Session, transaction: TransactionRequest):
    # check if we have a valid payment method
    account_used: Account | None = account_repo.get_account_by_name(session, transaction.payment_method_name)

    if account_used is None:
        raise ValueError("Payment method does not exist")

    # check if we have valid envelopes
    ledger_entry_list = transaction.ledger_entries
    for entry in ledger_entry_list:
        entry_db = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
        if entry_db is None:
            raise ValueError("Envelope does not exist")

    # create the master transaction
    master_transaction = transaction_repo.create_transaction(session, transaction)

    # make corresponding ledger entries and adding the envelopes
    ledger_db_entries = list()
    total_transaction = Decimal()
    for entry in ledger_entry_list:
        total_transaction = total_transaction + entry.amount
        entry_envelope = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
        new_entry = ledger_repo.add_ledger_entry(session, entry)
        new_entry.envelope = entry_envelope
        ledger_db_entries.append(new_entry)

    # append the new ledger entries to the master transaction
    master_transaction.entries = ledger_db_entries

    if account_used.account_type is AccountType.CASH:
        # deduct from cash balance
        account_used.current_balance -= abs(total_transaction)
    elif account_used.account_type is AccountType.CREDIT_CARD:
        pass
        # here is the case where we deduct from the envelope and we add to the cc payment envelope
    
    session.commit()
    session.refresh(master_transaction)
    return master_transaction

def add_financed_transaction(session: Session, transaction: TransactionRequest):
    pass