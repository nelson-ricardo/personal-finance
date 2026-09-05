"""Transaction processing and retrieval service.

Implements core double-entry accounting mechanics for:
- Regular transactions (Cash expenses, Credit Card expenses with automated balancing transfers).
- Financed installment transactions (creating dedicated envelopes with calculated monthly payments).
- Transaction querying, filtering, and total calculations with CC balancing entry exclusions.
"""

from datetime import date
from decimal import Decimal
from typing import List

from sqlmodel import Session

from budget_app.models import Account, Ledger, Transaction
from budget_app.repositories import (
    account_repo,
    envelope_repo,
    ledger_repo,
    transaction_repo,
)
from budget_app.schemas import (
    AccountType,
    EnvelopeBase,
    FinancedTransaction,
    LedgerRequest,
    LedgerResponse,
    TransactionDetailResponse,
    TransactionRequest,
    TransactionResponse,
    TransactionType,
    TransactionUpdateRequest,
)



def add_reg_transaction(session: Session, transaction: TransactionRequest) -> Transaction:

    """Processes a regular transaction (income, expense, or transfer) and updates account balances.

    If a Credit Card was used, the transaction total is added to the 'Credit Card Payment'
    envelope and increases the credit card's current balance (owed amount).
    If Cash was used, the transaction total is deducted from the cash balance.

    Args:
        session: Active SQLModel database session.
        transaction: TransactionRequest object containing payment method, ledger entries, etc.

    Returns:
        The created master Transaction instance.

    Raises:
        ValueError: If transaction_type is FINANCED (must use add_financed_transaction instead),
            or if the payment method account does not exist.
    """
    if transaction.transaction_type == TransactionType.FINANCED:
        raise ValueError("financed transaction should be processed through add_financed_transaction")

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


def add_financed_transaction(session: Session, transaction: FinancedTransaction) -> Transaction:
    """Processes a credit card financed transaction.

    Creates or fetches a designated envelope with a note indicating the calculated monthly payment,
    creates two offsetting ledger entries (net zero impact on the envelope), increases the credit
    card balance by the total financed amount, and creates a master transaction of type FINANCED.

    Args:
        session: Active SQLModel database session.
        transaction: FinancedTransaction containing merchant, amount, term, payment method, etc.

    Returns:
        The created master financed Transaction instance.

    Raises:
        ValueError: If merchant is empty/whitespace, term <= 0, payment method does not exist,
            payment method is not a Credit Card, or amount <= 0.
    """
    # ensure merchant is not empty or whitespace
    if not transaction.merchant or not transaction.merchant.strip():
        raise ValueError("Merchant name cannot be empty")

    # ensure we have a positive term
    if transaction.term <= 0:
        raise ValueError("Term has to be a positive number")

    # get the payment method, ensure existence, ensure it is credit card
    payment_method: Account | None = account_repo.get_account_by_name(
        session, transaction.payment_method_name
    )

    if not payment_method:
        raise ValueError(f"Account {transaction.payment_method_name} does not exist")

    if payment_method.account_type is not AccountType.CREDIT_CARD:
        raise ValueError("Account type has to be credit card")

    # ensure we have a positive, non-zero value as amount financed
    if transaction.amount <= Decimal("0"):
        raise ValueError("Amount financed has to be greater than 0")

    # get or create the envelope
    envelope_name: str

    # calculate the monthly payment with 2 decimal precision
    monthly_payment = round(transaction.amount / Decimal(transaction.term), 2)

    # create the envelope with the given name or generate a new one
    if transaction.envelope_name:
        envelope_name = transaction.envelope_name
    else:
        envelope_name = f"{transaction.merchant.strip()} - {transaction.term}"

    envelope_used = envelope_repo.get_or_create_envelope(session, EnvelopeBase(
        name=envelope_name,
        note=f"{monthly_payment}/mo."
    ))

    # make the transaction
    positive_entry = LedgerRequest(
        amount=transaction.amount,
        envelope_name=envelope_name
    )
    negative_entry = LedgerRequest(
        amount=-1*transaction.amount,
        envelope_name=envelope_name
    )

    master_transaction_req: TransactionRequest = TransactionRequest(
        merchant=transaction.merchant,
        logged_date=transaction.logged_date,
        posted_date=transaction.posted_date,
        note=transaction.note,
        is_reconciled=transaction.is_reconciled,
        payment_method_name=transaction.payment_method_name,
        transaction_type=TransactionType.FINANCED,
        ledger_entries=[positive_entry, negative_entry]
    )

    master_transaction: Transaction = transaction_repo.create_transaction(
        session,
        master_transaction_req
    )

    # update the balance
    payment_method.current_balance += transaction.amount
    session.add(payment_method)

    session.commit()
    session.refresh(master_transaction)
    return master_transaction


def calculate_transaction_total(transaction: Transaction) -> Decimal:
    """Calculates the total monetary amount for a transaction.

    For credit card regular expense transactions and their reversals, excludes the balancing
    entry associated with the 'Credit Card Payment' envelope.
    For financed transactions, returns the positive financed amount.
    For transfers, returns the transferred amount.

    Args:
        transaction: Transaction instance with populated entries and account relation.

    Returns:
        The total transaction amount as a positive Decimal.
    """
    if not transaction.entries:
        return Decimal("0.00")

    if transaction.transaction_type == TransactionType.FINANCED:
        return abs(transaction.entries[0].amount)

    if transaction.transaction_type == TransactionType.TRANSFER:
        return abs(transaction.entries[0].amount)

    is_credit_card = (
        transaction.account is not None
        and transaction.account.account_type == AccountType.CREDIT_CARD
    )

    total = Decimal("0.00")
    for entry in transaction.entries:
        # Filter out the credit card payment balancing entry
        if (
            is_credit_card
            and entry.envelope is not None
            and entry.envelope.name == "Credit Card Payment"
        ):
            continue
        total += abs(entry.amount)

    return total


def get_transactions(
    session: Session,
    *,
    limit: int | None = None,
    envelope: str | None = None,
    account: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    transaction_type: TransactionType | list[TransactionType] | None = None,
    include_reversed: bool = False,
    **kwargs,
) -> list[TransactionResponse]:
    """Fetches a set of transactions based on various filtering criteria.

    Transforms transactions into Pydantic models containing the transaction total
    (with credit card balancing entries filtered out). Automatically filters out
    REVERSAL transactions and reversed transactions by default unless include_reversed=True
    or transaction_type=TransactionType.REVERSAL is specified.

    Args:
        session: Active SQLModel database session.
        limit: Optional max number of transactions to return. Must be > 0 if specified.
        envelope: Optional envelope name (str) to filter by.
        account: Optional account name (str) to filter by.
        date_from: Optional start date (inclusive). Defaults to the 3rd of the current month.
        date_to: Optional end date (inclusive). Defaults to the 28th of the current month.
        transaction_type: Optional transaction type(s) from TransactionType enum to filter by.
            By default, returns all active transaction types except TRANSFER and REVERSAL (i.e. EXPENSE, INCOME, FINANCED).
        include_reversed: Whether to include reversed transactions and reversals (default False).

    Returns:
        List of TransactionResponse objects.

    Raises:
        ValueError: If limit <= 0, date_from > date_to, invalid transaction_type,
            or if the specified envelope or account does not exist.
    """
    # Support camelCase alias transactionType or legacy aliases if passed
    if "transactionType" in kwargs and transaction_type is None:
        transaction_type = kwargs["transactionType"]
    if "includeReversed" in kwargs:
        include_reversed = kwargs["includeReversed"]
    if "envelope_id" in kwargs and envelope is None:
        envelope = kwargs["envelope_id"]
    if "account_id" in kwargs and account is None:
        account = kwargs["account_id"]
    if "envelope_name" in kwargs and envelope is None:
        envelope = kwargs["envelope_name"]
    if "account_name" in kwargs and account is None:
        account = kwargs["account_name"]

    today = date.today()
    if date_from is None:
        date_from = date(today.year, today.month, 3)
    if date_to is None:
        date_to = date(today.year, today.month, 28)

    if date_from > date_to:
        raise ValueError(
            f"date_from ({date_from}) cannot be after date_to ({date_to})"
        )

    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")

    # Parse and validate transaction_type filter
    parsed_types: list[TransactionType]
    if transaction_type is None:
        # Default: all active transaction types but transfers and reversals
        parsed_types = [
            TransactionType.EXPENSE,
            TransactionType.INCOME,
            TransactionType.FINANCED,
        ]
    elif isinstance(transaction_type, (list, tuple, set)):
        parsed_types = []
        for t in transaction_type:
            if isinstance(t, TransactionType):
                parsed_types.append(t)
            elif isinstance(t, str):
                try:
                    parsed_types.append(TransactionType(t))
                except ValueError:
                    raise ValueError(f"Invalid transaction type: {t}. Must be a TransactionType enum member.")
            else:
                raise ValueError(f"Invalid transaction type: {t}. Must be a TransactionType enum member.")
    elif isinstance(transaction_type, TransactionType):
        parsed_types = [transaction_type]
    elif isinstance(transaction_type, str):
        try:
            parsed_types = [TransactionType(transaction_type)]
        except ValueError:
            raise ValueError(f"Invalid transaction type: {transaction_type}. Must be a TransactionType enum member.")
    else:
        raise ValueError(f"Invalid transaction_type format: {transaction_type}. Must be from TransactionType enum.")

    # Resolve envelope filter (accepts string name)
    resolved_env_id: int | None = None
    if envelope is not None:
        if not isinstance(envelope, str):
            raise ValueError(f"Envelope must be a string name, got {type(envelope).__name__}")
        env = envelope_repo.get_envelope_by_name(session, envelope.strip())
        if not env:
            raise ValueError(f"Envelope '{envelope}' does not exist")
        resolved_env_id = env.id

    # Resolve account filter (accepts string name)
    resolved_acc_id: int | None = None
    if account is not None:
        if not isinstance(account, str):
            raise ValueError(f"Account must be a string name, got {type(account).__name__}")
        acc = account_repo.get_account_by_name(session, account.strip())
        if not acc:
            raise ValueError(f"Account '{account}' does not exist")
        resolved_acc_id = acc.id

    # Find CC payment envelope ID for balancing entry filtering
    cc_env = envelope_repo.get_envelope_by_name(session, "Credit Card Payment")
    cc_env_id = cc_env.id if cc_env else None

    # Determine whether to exclude reversed transactions
    exclude_rev = not include_reversed and (TransactionType.REVERSAL not in parsed_types)

    # Query the repository
    transactions = transaction_repo.get_transactions(
        session,
        account_id=resolved_acc_id,
        envelope_id=resolved_env_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        transaction_types=parsed_types,
        exclude_balancing_for_envelope_id=cc_env_id,
        exclude_reversed=exclude_rev,
    )


    # Convert to response models with total calculations
    results: list[TransactionResponse] = []
    for tx in transactions:
        total = calculate_transaction_total(tx)
        payment_name = tx.account.name if tx.account else ""
        if tx.id is None or tx.payment_method_id is None:
            continue
        results.append(
            TransactionResponse(
                id=tx.id,
                merchant=tx.merchant,
                logged_date=tx.logged_date,
                posted_date=tx.posted_date,
                note=tx.note,
                is_reconciled=tx.is_reconciled,
                payment_method_id=tx.payment_method_id,
                payment_method_name=payment_name,
                transaction_type=tx.transaction_type,
                total=total,
            )
        )

    return results


def delete_transaction(session: Session, transaction_id: int) -> Transaction:
    """Reverses an existing transaction by creating a compensating reversal transaction.

    Inverts all child ledger entries, restores account balances appropriately according to
    the original transaction type (EXPENSE, INCOME, FINANCED, TRANSFER), and marks the original
    transaction as reversed in its note to preserve an immutable audit trail.

    Args:
        session: Active SQLModel database session.
        transaction_id: Integer ID of the transaction to delete/reverse.

    Returns:
        The newly created compensating reversal Transaction instance.

    Raises:
        ValueError: If transaction_id does not exist, transaction is already reversed,
            or if the transaction is missing required account/envelope relations.
    """
    og_tx = session.get(Transaction, transaction_id)
    if not og_tx:
        raise ValueError(f"Transaction with id: {transaction_id} does not exist.")

    # Guard against reversing a reversal or an already-reversed transaction
    if og_tx.transaction_type == TransactionType.REVERSAL or (og_tx.note and "[REVERSED]" in og_tx.note):
        raise ValueError(f"Transaction #{transaction_id} has already been reversed.")

    if not og_tx.account:
        raise ValueError(f"Transaction #{transaction_id} has no associated payment account.")

    # 1. Reverse all child ledger entries with inverted signs
    reverse_entries: list[LedgerRequest] = []
    for entry in og_tx.entries:
        if not entry.envelope:
            raise ValueError(f"Envelope for ledger entry #{entry.id} not found.")
        reverse_entries.append(
            LedgerRequest(
                amount=-1 * entry.amount,
                envelope_name=entry.envelope.name,
            )
        )

    # 2. Determine original total magnitude
    tx_total = calculate_transaction_total(og_tx)

    # 3. Create the compensating reversal transaction
    rev_tx_req = TransactionRequest(
        merchant=f"Reversal: {og_tx.merchant}",
        logged_date=date.today(),
        posted_date=None,
        note=f"Reversal of transaction #{transaction_id}",
        is_reconciled=False,
        payment_method_name=og_tx.account.name,
        transaction_type=TransactionType.REVERSAL,
        ledger_entries=reverse_entries,
    )
    reversal_tx = transaction_repo.create_transaction(session, rev_tx_req)

    # 4. Reverse account balance changes accurately
    account = og_tx.account
    if og_tx.transaction_type == TransactionType.EXPENSE:
        if account.account_type == AccountType.CASH:
            account.current_balance += tx_total
        elif account.account_type == AccountType.CREDIT_CARD:
            account.current_balance -= tx_total

    elif og_tx.transaction_type == TransactionType.INCOME:
        if account.account_type == AccountType.CASH:
            account.current_balance -= tx_total

    elif og_tx.transaction_type == TransactionType.FINANCED:
        account.current_balance -= tx_total

    # 5. Mark original transaction as reversed in notes
    og_tx.note = f"[REVERSED] {og_tx.note}" if og_tx.note else "[REVERSED]"
    session.add(account)
    session.add(og_tx)

    session.commit()
    session.refresh(reversal_tx)
    return reversal_tx


def get_transaction_by_id(session: Session, transaction_id: int) -> TransactionDetailResponse:
    """Fetches a single transaction with its metadata, payment account name, and ledger split entries.

    Args:
        session: Active SQLModel database session.
        transaction_id: Integer ID of the transaction to look up.

    Returns:
        TransactionDetailResponse containing full transaction metadata, account name,
        computed total, and list of child LedgerResponse entries with envelope information.

    Raises:
        ValueError: If the transaction with the specified ID does not exist.
    """
    tx = transaction_repo.get_transaction_by_id(session, transaction_id)
    if not tx:
        raise ValueError(f"Transaction with id: {transaction_id} does not exist.")

    total = calculate_transaction_total(tx)
    payment_name = tx.account.name if tx.account else ""

    if tx.id is None or tx.payment_method_id is None:
        raise ValueError(f"Transaction #{transaction_id} is missing required identifiers.")

    ledger_entries = [
        LedgerResponse(
            id=entry.id,
            amount=entry.amount,
            envelope_id=entry.envelope_id,
            envelope_name=entry.envelope.name if entry.envelope else "",
        )
        for entry in tx.entries
        if entry.id is not None and entry.envelope_id is not None
    ]

    return TransactionDetailResponse(
        id=tx.id,
        merchant=tx.merchant,
        logged_date=tx.logged_date,
        posted_date=tx.posted_date,
        note=tx.note,
        is_reconciled=tx.is_reconciled,
        payment_method_id=tx.payment_method_id,
        payment_method_name=payment_name,
        transaction_type=tx.transaction_type,
        total=total,
        entries=ledger_entries,
    )


def update_transaction(
    session: Session, transaction_id: int, updates: TransactionUpdateRequest
) -> Transaction:
    """Modifies an existing transaction in-place while maintaining accounting integrity.

    Supports metadata updates (merchant, note, dates, reconciliation status), split
    amount and envelope adjustments, and payment account reassignment.
    Reconciled transactions only permit metadata updates (notes, merchant, dates); their
    ledger splits and payment accounts cannot be modified. Financed and reversed
    transactions cannot be modified through this function.

    Args:
        session: Active SQLModel database session.
        transaction_id: Integer ID of the transaction to modify.
        updates: TransactionUpdateRequest containing fields to update.

    Returns:
        The updated and refreshed Transaction instance.

    Raises:
        ValueError: If transaction doesn't exist, is FINANCED or REVERSAL, has been
            reversed, is reconciled and financial fields are modified, has invalid
            merchant, or if the target account or envelopes do not exist.
    """
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise ValueError(f"Transaction with id: {transaction_id} does not exist.")

    if tx.transaction_type == TransactionType.FINANCED:
        raise ValueError(
            "Financed transactions cannot be modified through this function."
        )

    is_reversal = tx.transaction_type == TransactionType.REVERSAL
    has_reversed_note = bool(tx.note and "[REVERSED]" in tx.note)
    if is_reversal or has_reversed_note:
        raise ValueError(
            f"Transaction #{transaction_id} has been reversed and cannot be modified."
        )

    if not tx.account:
        raise ValueError(
            f"Transaction #{transaction_id} has no associated payment account."
        )

    # Check reconciled constraints
    if tx.is_reconciled:
        if updates.ledger_entries is not None:
            raise ValueError(
                "Cannot modify ledger entries of a reconciled transaction."
            )
        if (
            updates.payment_method_name is not None
            and updates.payment_method_name != tx.account.name
        ):
            raise ValueError(
                "Cannot change the payment method of a reconciled transaction."
            )

    # Metadata updates
    if updates.merchant is not None:
        if not updates.merchant.strip():
            raise ValueError("Merchant name cannot be empty.")
        tx.merchant = updates.merchant.strip()

    if updates.logged_date is not None:
        tx.logged_date = updates.logged_date

    if updates.posted_date is not None:
        tx.posted_date = updates.posted_date

    if updates.note is not None:
        tx.note = updates.note

    if updates.is_reconciled is not None:
        tx.is_reconciled = updates.is_reconciled

    # Determine if financial/structural updates are needed
    is_financial_update = (
        updates.ledger_entries is not None
        or (
            updates.payment_method_name is not None
            and updates.payment_method_name != tx.account.name
        )
    )

    if is_financial_update:
        # Resolve target payment account
        target_account = tx.account
        if updates.payment_method_name is not None:
            acc = account_repo.get_account_by_name(session, updates.payment_method_name)
            if not acc:
                raise ValueError(
                    f"Account {updates.payment_method_name} does not exist."
                )
            target_account = acc

        # Resolve target splits
        if updates.ledger_entries is not None:
            if not updates.ledger_entries:
                raise ValueError("Transaction must have at least one ledger entry.")
            target_split_requests = updates.ledger_entries
        else:
            # Preserve existing splits, excluding CC payment balancing entry
            is_old_cc = tx.account.account_type == AccountType.CREDIT_CARD
            target_split_requests = []
            for entry in tx.entries:
                if not entry.envelope:
                    raise ValueError(
                        f"Envelope for ledger entry #{entry.id} not found."
                    )
                if is_old_cc and entry.envelope.name == "Credit Card Payment":
                    continue
                target_split_requests.append(
                    LedgerRequest(
                        amount=entry.amount,
                        envelope_name=entry.envelope.name,
                    )
                )

        # Validate that all envelopes exist
        envelopes_by_name = {}
        for entry_req in target_split_requests:
            env = envelope_repo.get_envelope_by_name(session, entry_req.envelope_name)
            if not env:
                raise ValueError(f"Envelope {entry_req.envelope_name} does not exist.")
            envelopes_by_name[entry_req.envelope_name] = env

        # 1. Undo old financial impact on old account
        old_account = tx.account
        old_total = calculate_transaction_total(tx)

        if tx.transaction_type == TransactionType.EXPENSE:
            if old_account.account_type == AccountType.CASH:
                old_account.current_balance += old_total
            elif old_account.account_type == AccountType.CREDIT_CARD:
                old_account.current_balance -= old_total
        elif tx.transaction_type == TransactionType.INCOME:
            if old_account.account_type == AccountType.CASH:
                old_account.current_balance -= old_total

        # 2. Delete old ledger splits
        for entry in list(tx.entries):
            session.delete(entry)
        tx.entries.clear()

        # 3. Create new user ledger splits
        new_total = Decimal("0.00")
        for entry_req in target_split_requests:
            env = envelopes_by_name[entry_req.envelope_name]
            tx.entries.append(Ledger(amount=entry_req.amount, envelope=env))
            new_total += abs(entry_req.amount)

        # 4. If target account is CC and transaction is Expense, add balancing entry
        if (
            target_account.account_type == AccountType.CREDIT_CARD
            and tx.transaction_type == TransactionType.EXPENSE
        ):
            cc_env = envelope_repo.get_or_create_envelope(
                session, EnvelopeBase(name="Credit Card Payment")
            )
            tx.entries.append(Ledger(amount=new_total, envelope=cc_env))

        # 5. Apply new financial impact on target account
        if tx.transaction_type == TransactionType.EXPENSE:
            if target_account.account_type == AccountType.CASH:
                target_account.current_balance -= new_total
            elif target_account.account_type == AccountType.CREDIT_CARD:
                target_account.current_balance += new_total
        elif tx.transaction_type == TransactionType.INCOME:
            if target_account.account_type == AccountType.CASH:
                target_account.current_balance += new_total

        # Bind transaction to target account
        tx.account = target_account

        session.add(old_account)
        if target_account != old_account:
            session.add(target_account)

    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


# Aliases
get_transaction = get_transactions
fetch_transactions = get_transactions
reverse_transaction = delete_transaction
fetch_transaction_by_id = get_transaction_by_id
get_transaction_detail = get_transaction_by_id
fetch_transaction_detail = get_transaction_by_id
modify_transaction = update_transaction