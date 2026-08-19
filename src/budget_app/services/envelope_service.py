from decimal import Decimal

from sqlmodel import Session

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories import account_repo, envelope_repo, transaction_repo
from budget_app.schemas import (
    EnvelopeBase,
    EnvelopeTransfer,
    LedgerRequest,
    TransactionRequest,
    TransactionType,
)


def create_envelope(
    session: Session, envelope_info: EnvelopeBase
) -> Envelope:
    """Creates a new envelope and persists it in the database.

    Args:
        session: Active SQLModel database session.
        envelope_info: Information for the envelope being created (name, note, is_active).

    Returns:
        The newly created and refreshed Envelope instance.

    Raises:
        ValueError: If name is empty/whitespace or an envelope with the given name already exists.
    """
    if not envelope_info.name or not envelope_info.name.strip():
        raise ValueError("Envelope name cannot be empty")

    envelope_info.name = envelope_info.name.strip()

    new_envelope = envelope_repo.create_envelope(session, envelope_info)
    session.commit()
    session.refresh(new_envelope)

    return new_envelope


def add_to_cash(
    session: Session, amount: Decimal, source: str, note: str | None = None
) -> Transaction:
    """Adds income to the Cash account balance and assigns it to the 'Unassigned' envelope.

    Args:
        session: Active SQLModel database session.
        amount: Positive amount of income being added.
        source: Name of the income source or merchant.
        note: Optional note detailing the income transaction.

    Returns:
        The created master income Transaction instance.

    Raises:
        ValueError: If amount is negative.
        RuntimeError: If default 'Cash' account or 'Unassigned' envelope do not exist.
    """
    # makes sure we are entering a valid amount in cash
    if amount < Decimal("0.00"):
        raise ValueError("add_to_cash error: cannot add negative amounts")

    # fetch the cash account and the unassigned envelope
    cash_account: Account | None = account_repo.get_account_by_name(session, "Cash")
    unassigned_envelope: Envelope | None = (
        envelope_repo.get_envelope_by_name(session, "Unassigned")
    )

    # check if we fetched the envelope and cash accounts
    if not unassigned_envelope:
        raise RuntimeError(
            "System error: Default 'Unassigned' envelope does not exist."
        )
    if not cash_account:
        raise RuntimeError("System error: Default 'Cash' account does not exist.")

    # create the master transaction to add money
    entry: LedgerRequest = LedgerRequest(amount=amount, envelope_name="Unassigned")
    master_tx_req: TransactionRequest = TransactionRequest(
        merchant=source,
        note=note,
        payment_method_name="Cash",
        transaction_type=TransactionType.INCOME,
        ledger_entries=[entry],
    )
    master_transaction: Transaction = transaction_repo.create_transaction(
        session, master_tx_req
    )

    # add money to the account
    cash_account.current_balance += amount
    session.add(cash_account)

    session.commit()
    session.refresh(master_transaction)
    return master_transaction


def transfer_between_envelopes(
    session: Session, source: str, destination: str, amount: Decimal
) -> EnvelopeTransfer:
    """Transfers funds between two envelopes and records a transfer transaction.

    Args:
        session: Active SQLModel database session.
        source: Name of the envelope to deduct funds from.
        destination: Name of the envelope to receive funds.
        amount: Positive amount of money to transfer.

    Returns:
        EnvelopeTransfer containing source/destination envelopes, updated balances,
        and the recorded transfer Transaction instance.

    Raises:
        ValueError: If source equals destination, amount is <= 0, either envelope
            does not exist, or the source envelope has insufficient funds.
    """

    if source == destination:
        raise ValueError("transfer_between_envelopes: source cannot equal destination")

    if amount <= 0:
        raise ValueError("transfer_between_envelopes: amount cannot be 0 or negative")
    # get the source envelope and ensure it is not none
    src_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, source
    )
    if not src_envelope:
        raise ValueError("transfer_between_envelopes: source envelope does not exist")

    # get the destination envelope and ensure it is not none
    dest_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, destination
    )
    if not dest_envelope:
        raise ValueError(
            "transfer_between_envelopes: destination envelope does not exist"
        )

    # ensure source envelope has enough balance to transfer from
    src_envelope_bal: Decimal = envelope_repo.get_balance_for_envelope(
        session, src_envelope
    )
    if amount > src_envelope_bal:
        raise ValueError(
            f"transfer_between_envelopes: amount too high, can transfer up to {src_envelope_bal} from {source}"
        )

    # create master transaction
    ledger_entry_src: LedgerRequest = LedgerRequest(
        amount=amount * -1, envelope_name=source
    )
    ledger_entry_dest: LedgerRequest = LedgerRequest(
        amount=amount, envelope_name=destination
    )

    transaction_request = TransactionRequest(
        merchant=f"transfer {source} -> {destination}",
        payment_method_name="Cash",
        transaction_type=TransactionType.TRANSFER,
        ledger_entries=[ledger_entry_src, ledger_entry_dest],
    )
    master_transaction: Transaction = transaction_repo.create_transaction(
        session, transaction_request
    )

    session.commit()
    session.refresh(master_transaction)

    return EnvelopeTransfer(
        source=src_envelope,
        new_balance_src=envelope_repo.get_balance_for_envelope(session, src_envelope),
        destination=dest_envelope,
        new_balance_dest=envelope_repo.get_balance_for_envelope(session, dest_envelope),
        transfer_transaction=master_transaction,
    )
