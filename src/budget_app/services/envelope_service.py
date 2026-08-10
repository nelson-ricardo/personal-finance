from decimal import Decimal

from sqlmodel import Session

from budget_app.models import envelope as envelope_db
from budget_app.schemas import envelope as envelope_schema
from budget_app.repositories import envelope_repo, ledger_repo, transaction_repo
from budget_app.repositories.account_repo import get_account_by_name
from budget_app.schemas.ledger import LedgerRequest
from budget_app.models.account import Account
from budget_app.models.transaction import Transaction
from budget_app.schemas.transaction import TransactionRequest

def create_envelope(session: Session, envelope_info: envelope_schema.EnvelopeBase) -> envelope_db.Envelope:
    """
        Create a new envelope using EnvelopeBase\n
        session: Session object used to interface with the database\n
        envelope_info: information about the envelope being created
    """
    new_envelope = envelope_repo.create_envelope(session, envelope_info)
    session.commit()
    session.refresh(new_envelope)

    return new_envelope

def add_to_cash(session: Session, amount: Decimal, source: str, note: str | None = None) -> Transaction:

    """
        Function specifically to add a balance to cash and add to the
        'Unassigned' envelope.\n
        amount: amount of money being added to the account\n
        source: source of the money added\n
        note: additional information of the income\n
    """
    # makes sure we are entering a valid amount in cash
    if amount < Decimal("0.00"):
        raise ValueError("add_to_cash error: cannot add negative amounts")

    # fetch the cash account and the unassigned envelope
    cash_account: Account | None = get_account_by_name(session, "Cash")
    unassigned_envelope: envelope_db.Envelope | None = envelope_repo.get_envelope_by_name(session, "Unassigned")

    # check if we fetched the envelope and cash accounts
    if not unassigned_envelope:
        raise RuntimeError("System error: Default 'Unassigned' envelope does not exist.")
    if not cash_account:
        raise RuntimeError("System error: Default 'Cash' account does not exist.")

    # create the master transaction to add money
    entry: LedgerRequest = LedgerRequest(amount=amount, envelope_name="Cash")
    master_tx_req: TransactionRequest = TransactionRequest(
        merchant=source,
        note=note,
        is_financed= False,
        payment_method_name="Cash",
        ledger_entries=[entry]
    )
    master_transaction: Transaction = transaction_repo.create_transaction(
        session, 
        master_tx_req
    )

    # create the necessary entry
    db_entry = ledger_repo.add_ledger_entry(session, entry)

    # add the necessary links between the transaction, envelope, and entry
    master_transaction.entries = [db_entry]
    master_transaction.account = cash_account
    db_entry.envelope = unassigned_envelope

    # add money to the account
    cash_account.current_balance += amount
    session.add(cash_account)

    session.commit()
    session.refresh(master_transaction)
    return master_transaction