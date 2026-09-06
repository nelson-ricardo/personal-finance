"""Envelope management and fund allocation service.

Handles:
- Creating custom budgeting envelopes.
- Adding cash income into the default 'Unassigned' envelope.
- Transferring money between envelopes (with balance validation).
- Allocating funds from 'Unassigned' to specific budgeting envelopes.
"""

from decimal import Decimal
from typing import List

from sqlmodel import Session

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories import account_repo, envelope_repo, transaction_repo
from budget_app.schemas import (
    EnvelopeBase,
    EnvelopeTransfer,
    LedgerRequest,
    TransactionRequest,
    TransactionType,
    EnvelopeWithBalance,
    EnvelopeUpdate,
)

SYSTEM_ENVELOPES: frozenset[str] = frozenset({"Unassigned", "Credit Card Payment"})


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
        ValueError: If source or destination is empty/whitespace, source equals destination,
            amount is <= 0, either envelope does not exist, or the source envelope has insufficient funds.
    """
    if not source or not source.strip():
        raise ValueError("transfer_between_envelopes: source envelope cannot be empty")

    if not destination or not destination.strip():
        raise ValueError("transfer_between_envelopes: destination envelope cannot be empty")

    source = source.strip()
    destination = destination.strip()

    if source == destination:
        raise ValueError("transfer_between_envelopes: source cannot equal destination")

    if amount <= Decimal("0"):
        raise ValueError("transfer_between_envelopes: amount cannot be 0 or negative")

    # get the source envelope and ensure it is not none
    src_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, source
    )
    if not src_envelope:
        raise ValueError(
            f"transfer_between_envelopes: source envelope '{source}' does not exist"
        )

    # get the destination envelope and ensure it is not none
    dest_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, destination
    )
    if not dest_envelope:
        raise ValueError(
            f"transfer_between_envelopes: destination envelope '{destination}' does not exist"
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


def assign_to_envelope(
    session: Session, destination: str, amount: Decimal
) -> EnvelopeTransfer:
    """Transfers funds from the 'Unassigned' envelope to a specified destination envelope.

    Args:
        session: Active SQLModel database session.
        destination: Name of the envelope to receive funds.
        amount: Positive amount of money to allocate from Unassigned.

    Returns:
        EnvelopeTransfer containing source (Unassigned) and destination envelopes,
        updated balances, and the recorded transfer Transaction instance.

    Raises:
        ValueError: If destination is empty/whitespace, destination is 'Unassigned',
            amount <= 0, destination envelope does not exist, or Unassigned envelope
            has insufficient funds.
    """
    return transfer_between_envelopes(
        session=session,
        source="Unassigned",
        destination=destination,
        amount=amount,
    )

def deactivate_envelope(session: Session, envelope_name: str) -> Envelope:
    """Deactivates an envelope if its current balance is zero.

    Args:
        session: Active SQLModel database session.
        envelope_name: Name of the envelope to deactivate.

    Returns:
        The deactivated (or already inactive) Envelope instance.

    Raises:
        ValueError: If envelope name is empty/whitespace, envelope does not exist,
            envelope is a protected system or linked envelope, or balance is non-zero.
    """
    if not envelope_name or not envelope_name.strip():
        raise ValueError("deactivate_envelope: envelope name cannot be empty")

    envelope_name = envelope_name.strip()

    if envelope_name in SYSTEM_ENVELOPES:
        raise ValueError(f"Cannot deactivate system envelope '{envelope_name}'")

    target_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, envelope_name
    )

    if not target_envelope:
        raise ValueError(f"envelope '{envelope_name}' does not exist")

    if target_envelope.account is not None:
        raise ValueError(
            f"Cannot deactivate envelope '{envelope_name}' linked to account '{target_envelope.account.name}'"
        )

    if not target_envelope.is_active:
        return target_envelope

    current_balance = envelope_repo.get_balance_for_envelope(session, target_envelope)
    if current_balance != Decimal("0"):
        raise ValueError(
            f"envelope '{envelope_name}' has a balance ({current_balance}), needs to be zero before deactivating"
        )

    target_envelope.is_active = False
    session.add(target_envelope)
    session.commit()
    session.refresh(target_envelope)
    return target_envelope


def activate_envelope(session: Session, envelope_name: str) -> Envelope:
    """Activates an envelope.

    Args:
        session: Active SQLModel database session.
        envelope_name: Name of the envelope to activate.

    Returns:
        The activated (or already active) Envelope instance.

    Raises:
        ValueError: If envelope name is empty/whitespace or envelope does not exist.
    """
    if not envelope_name or not envelope_name.strip():
        raise ValueError("activate_envelope: envelope name cannot be empty")

    envelope_name = envelope_name.strip()

    target_envelope: Envelope | None = envelope_repo.get_envelope_by_name(
        session, envelope_name
    )

    if not target_envelope:
        raise ValueError(f"envelope '{envelope_name}' does not exist")

    if target_envelope.is_active:
        return target_envelope

    target_envelope.is_active = True
    session.add(target_envelope)
    session.commit()
    session.refresh(target_envelope)
    return target_envelope

def get_envelopes_and_balances(
    session: Session, is_active: bool | None = None
) -> List[EnvelopeWithBalance]:
    """Fetches envelopes with their calculated balances, optionally filtered by active status.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all envelopes.

    Returns:
        List of EnvelopeWithBalance instances ordered by name.
    """
    envelopes = envelope_repo.get_envelopes(session, is_active)
    result: List[EnvelopeWithBalance] = []

    for envelope in envelopes:
        curr_balance = envelope_repo.get_balance_for_envelope(session, envelope)
        result.append(
            EnvelopeWithBalance(
                id=envelope.id,
                name=envelope.name,
                note=envelope.note,
                is_active=envelope.is_active,
                balance=curr_balance,
            )
        )

    return result


def get_active_envelopes_w_balance(session: Session) -> List[EnvelopeWithBalance]:
    """Retrieves all active budgeting envelopes with their current balances."""
    return get_envelopes_and_balances(session, is_active=True)


def get_inactive_envelopes_w_balance(session: Session) -> List[EnvelopeWithBalance]:
    """Retrieves all inactive budgeting envelopes with their current balances."""
    return get_envelopes_and_balances(session, is_active=False)


def get_single_envelope_w_balance(
    session: Session, envelope_name: str
) -> EnvelopeWithBalance:
    """Fetches a single envelope and its calculated balance.

    Args:
        session: Active SQLModel database session.
        envelope_name: Name of the envelope to retrieve.

    Returns:
        EnvelopeWithBalance instance with current balance.

    Raises:
        ValueError: If name is empty/whitespace or envelope does not exist.
    """
    if not envelope_name or not envelope_name.strip():
        raise ValueError("get_single_envelope_w_balance: envelope name cannot be empty")

    envelope_name = envelope_name.strip()
    target_envelope = envelope_repo.get_envelope_by_name(session, envelope_name)

    if not target_envelope:
        raise ValueError(f"envelope '{envelope_name}' does not exist")

    curr_balance = envelope_repo.get_balance_for_envelope(session, target_envelope)

    return EnvelopeWithBalance(
        id=target_envelope.id,
        name=target_envelope.name,
        note=target_envelope.note,
        is_active=target_envelope.is_active,
        balance=curr_balance,
    )


def perma_delete_envelope(session: Session, envelope_name: str) -> bool:
    """Permanently deletes an envelope if it has no associated ledger transactions.

    System envelopes and envelopes linked to financial accounts cannot be deleted.

    Args:
        session: Active SQLModel database session.
        envelope_name: Name of the envelope to delete.

    Returns:
        True if the envelope was deleted successfully.

    Raises:
        ValueError: If name is empty, envelope does not exist, envelope is a system
            envelope, envelope is linked to an account, or envelope has ledger entries.
    """
    if not envelope_name or not envelope_name.strip():
        raise ValueError("perma_delete_envelope: envelope name cannot be empty")

    envelope_name = envelope_name.strip()

    if envelope_name in SYSTEM_ENVELOPES:
        raise ValueError(f"Cannot delete system envelope '{envelope_name}'")

    target_envelope = envelope_repo.get_envelope_by_name(session, envelope_name)
    if not target_envelope:
        raise ValueError(f"envelope '{envelope_name}' does not exist")

    if target_envelope.account is not None:
        raise ValueError(
            f"Cannot delete envelope '{envelope_name}' linked to account '{target_envelope.account.name}'"
        )

    if target_envelope.id is not None and envelope_repo.has_ledger_entries(
        session, target_envelope.id
    ):
        raise ValueError(
            f"envelope '{envelope_name}' has transactions associated with it, deactivate it instead"
        )

    envelope_repo.delete_envelope(session, target_envelope)
    session.commit()
    return True


def update_envelope_info(
    session: Session,
    target_name: str,
    envelope_info: EnvelopeUpdate,
) -> Envelope:
    """Updates an envelope's name and/or note.

    Args:
        session: Active SQLModel database session.
        target_name: Current name of the envelope to update.
        envelope_info: EnvelopeUpdate payload with optional new name and note.

    Returns:
        The updated and refreshed Envelope instance.

    Raises:
        ValueError: If target name is empty, envelope does not exist, attempting
            to rename a system envelope, new name is invalid/duplicate, or new name
            is a protected system envelope name.
    """
    if not target_name or not target_name.strip():
        raise ValueError("update_envelope_info: envelope name cannot be empty")

    target_name = target_name.strip()

    target_envelope = envelope_repo.get_envelope_by_name(session, target_name)
    if not target_envelope:
        raise ValueError(f"envelope '{target_name}' does not exist")

    # If updating name
    if envelope_info.name is not None:
        new_name = envelope_info.name.strip()
        if not new_name:
            raise ValueError("Envelope name cannot be empty")

        if target_name in SYSTEM_ENVELOPES and new_name != target_name:
            raise ValueError(f"Cannot rename system envelope '{target_name}'")

        if new_name in SYSTEM_ENVELOPES and new_name != target_name:
            raise ValueError(f"Cannot rename envelope to protected system name '{new_name}'")

        if new_name != target_envelope.name:
            existing = envelope_repo.get_envelope_by_name(session, new_name)
            if existing is not None and existing.id != target_envelope.id:
                raise ValueError(f"envelope '{new_name}' already exists, try a different name")
            target_envelope.name = new_name

    # If updating note
    if envelope_info.note is not None:
        note_val = envelope_info.note.strip()
        target_envelope.note = note_val if note_val else None

    session.add(target_envelope)
    session.commit()
    session.refresh(target_envelope)
    return target_envelope



transfer_from_unassigned = assign_to_envelope
assign_from_unassigned = assign_to_envelope


