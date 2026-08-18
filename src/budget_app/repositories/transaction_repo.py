from sqlmodel import Session

from budget_app.models import Ledger, Transaction
from budget_app.repositories import account_repo, envelope_repo
from budget_app.schemas import TransactionRequest


def create_transaction(
    session: Session, transaction_info: TransactionRequest
) -> Transaction:
    # get the payment method
    account = account_repo.get_account_by_name(
        session, transaction_info.payment_method_name
    )
    if not account:
        raise ValueError(
            f"Account {transaction_info.payment_method_name} does not exist."
        )

    # generate the ledger entries
    envelopes_by_name = {}
    for entry in transaction_info.ledger_entries:
        env = envelope_repo.get_envelope_by_name(session, entry.envelope_name)
        if not env:
            raise ValueError(f"Envelope {entry.envelope_name} does not exist.")
        envelopes_by_name[entry.envelope_name] = env

    ledger_entries_db = [
        Ledger(
            amount=entry.amount, envelope=envelopes_by_name[entry.envelope_name]
        )
        for entry in transaction_info.ledger_entries
    ]

    # make the final transaction and add it to the session
    transaction: Transaction = Transaction(
        merchant=transaction_info.merchant,
        account=account,
        entries=ledger_entries_db,
        transaction_type=transaction_info.transaction_type,
    )

    session.add(transaction)
    return transaction
