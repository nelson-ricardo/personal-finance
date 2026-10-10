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

from budget_app.models import Account, EnvelopeSplit, Ledger, Transaction
from budget_app.repositories import (
    account_repo,
    category_repo,
    envelope_repo,
    envelope_split_repo,
    ledger_repo,
    transaction_repo,
)
from budget_app.schemas import (
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    EnvelopeSplitResponse,
    FinancedTransaction,
    FinancedTransactionUpdateRequest,
    LedgerRequest,
    LedgerResponse,
    SystemEnvelopeType,
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
        transaction: TransactionRequest object containing payment method, envelope splits, etc.

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
    for split in transaction.splits:
        transaction_total += abs(split.amount)

    master_transaction: Transaction = transaction_repo.create_transaction(session, transaction)

    # move money to credit card payment to balance the transaction out
    if payment_method.account_type is AccountType.CREDIT_CARD:
        cc_env = (
            payment_method.envelope
            or envelope_repo.get_envelope_by_system_role(
                session, SystemEnvelopeType.CREDIT_CARD_PAYMENT
            )
            or envelope_repo.get_envelope_by_name(session, "Credit Card Payment")
        )
        if not cc_env:
            raise RuntimeError(
                "System error: Credit card payment envelope does not exist."
            )
        cc_payment = envelope_split_repo.add_envelope_split(
            session, 
            EnvelopeSplitRequest(
                amount=transaction_total,
                envelope_id=cc_env.id,
                envelope_name=cc_env.name,
            )
        )
        master_transaction.splits.append(cc_payment)

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

    fixed_cat = category_repo.get_category_by_name(session, "Fixed Monthly Expenses")
    cat_id = fixed_cat.id if fixed_cat else None
    envelope_used = envelope_repo.get_or_create_envelope(
        session,
        EnvelopeBase(
            name=envelope_name,
            note=f"{monthly_payment}/mo.",
        ),
        category_id=cat_id,
    )
    if cat_id is not None and envelope_used.category_id is None:
        envelope_used.category_id = cat_id

    # make the transaction
    positive_entry = EnvelopeSplitRequest(
        amount=transaction.amount,
        envelope_name=envelope_name
    )
    negative_entry = EnvelopeSplitRequest(
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
        splits=[positive_entry, negative_entry]
    )

    master_transaction: Transaction = transaction_repo.create_transaction(
        session,
        master_transaction_req
    )

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
        transaction: Transaction instance with populated splits and account relation.

    Returns:
        The total transaction amount as a positive Decimal.
    """
    if not transaction.splits:
        return Decimal("0.00")

    if transaction.transaction_type in (
        TransactionType.FINANCED,
        TransactionType.TRANSFER,
        TransactionType.INTEREST_CHARGE,
        TransactionType.INTEREST_EARNED,
    ):
        return abs(transaction.splits[0].amount)

    is_credit_card = (
        transaction.account is not None
        and transaction.account.account_type == AccountType.CREDIT_CARD
    )

    total = Decimal("0.00")
    for split in transaction.splits:
        # Filter out the credit card payment balancing entry
        if (
            is_credit_card
            and split.envelope is not None
            and (
                split.envelope.system_role == SystemEnvelopeType.CREDIT_CARD_PAYMENT
                or (
                    transaction.account is not None
                    and transaction.account.envelope_id is not None
                    and split.envelope_id == transaction.account.envelope_id
                )
                or split.envelope.name == "Credit Card Payment"
            )
        ):
            continue
        total += abs(split.amount)

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
    cc_env = (
        envelope_repo.get_envelope_by_system_role(
            session, SystemEnvelopeType.CREDIT_CARD_PAYMENT
        )
        or envelope_repo.get_envelope_by_name(session, "Credit Card Payment")
    )
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

    # 1. Reverse all child envelope splits with inverted signs
    reverse_splits: list[EnvelopeSplitRequest] = []
    for split in og_tx.splits:
        if not split.envelope:
            raise ValueError(f"Envelope for envelope split #{split.id} not found.")
        reverse_splits.append(
            EnvelopeSplitRequest(
                amount=-1 * split.amount,
                envelope_name=split.envelope.name,
            )
        )

    # 2. Create the compensating reversal transaction
    rev_tx_req = TransactionRequest(
        merchant=f"Reversal: {og_tx.merchant}",
        logged_date=date.today(),
        posted_date=None,
        note=f"Reversal of transaction #{transaction_id}",
        is_reconciled=False,
        payment_method_name=og_tx.account.name,
        transaction_type=TransactionType.REVERSAL,
        splits=reverse_splits,
    )
    reversal_tx = transaction_repo.create_transaction(session, rev_tx_req)

    # 4. Mark original transaction as reversed in notes
    og_tx.note = f"[REVERSED] {og_tx.note}" if og_tx.note else "[REVERSED]"
    session.add(og_tx)

    session.commit()
    session.refresh(reversal_tx)
    return reversal_tx


def get_transaction_by_id(session: Session, transaction_id: int) -> TransactionDetailResponse:
    """Fetches a single transaction with its metadata, payment account name, and envelope split entries.

    Args:
        session: Active SQLModel database session.
        transaction_id: Integer ID of the transaction to look up.

    Returns:
        TransactionDetailResponse containing full transaction metadata, account name,
        computed total, and list of child EnvelopeSplitResponse entries with envelope information.

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

    envelope_splits = [
        EnvelopeSplitResponse(
            id=split.id,
            amount=split.amount,
            envelope_id=split.envelope_id,
            envelope_name=split.envelope.name if split.envelope else "",
        )
        for split in tx.splits
        if split.id is not None and split.envelope_id is not None
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
        splits=envelope_splits,
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
        if updates.splits is not None:
            raise ValueError(
                "Cannot modify envelope splits of a reconciled transaction."
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
        updates.splits is not None
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
        if updates.splits is not None:
            if not updates.splits:
                raise ValueError("Transaction must have at least one envelope split.")
            target_split_requests = updates.splits
        else:
            # Preserve existing splits, excluding CC payment balancing entry
            is_old_cc = tx.account.account_type == AccountType.CREDIT_CARD
            target_split_requests = []
            for split in tx.splits:
                if not split.envelope:
                    raise ValueError(
                        f"Envelope for envelope split #{split.id} not found."
                    )
                if is_old_cc and (
                    split.envelope.system_role == SystemEnvelopeType.CREDIT_CARD_PAYMENT
                    or (
                        tx.account is not None
                        and tx.account.envelope_id is not None
                        and split.envelope_id == tx.account.envelope_id
                    )
                    or split.envelope.name == "Credit Card Payment"
                ):
                    continue
                target_split_requests.append(
                    EnvelopeSplitRequest(
                        amount=split.amount,
                        envelope_name=split.envelope.name,
                    )
                )

        # Validate that all envelopes exist
        envelopes_by_name = {}
        for split_req in target_split_requests:
            env = envelope_repo.get_envelope_by_name(session, split_req.envelope_name)
            if not env:
                raise ValueError(f"Envelope {split_req.envelope_name} does not exist.")
            envelopes_by_name[split_req.envelope_name] = env

        # 1. Delete old envelope splits
        for split in list(tx.splits):
            session.delete(split)
        tx.splits.clear()

        # 2. Create new user envelope splits
        new_total = Decimal("0.00")
        for split_req in target_split_requests:
            env = envelopes_by_name[split_req.envelope_name]
            tx.splits.append(EnvelopeSplit(amount=split_req.amount, envelope=env))
            new_total += abs(split_req.amount)

        # 3. If target account is CC and transaction is Expense, add balancing entry
        if (
            target_account.account_type == AccountType.CREDIT_CARD
            and tx.transaction_type == TransactionType.EXPENSE
        ):
            cc_env = (
                target_account.envelope
                or envelope_repo.get_envelope_by_system_role(
                    session, SystemEnvelopeType.CREDIT_CARD_PAYMENT
                )
                or envelope_repo.get_or_create_envelope(
                    session,
                    EnvelopeBase(
                        name="Credit Card Payment",
                        system_role=SystemEnvelopeType.CREDIT_CARD_PAYMENT,
                    ),
                )
            )
            tx.splits.append(EnvelopeSplit(amount=new_total, envelope=cc_env))

        # Bind transaction to target account
        tx.account = target_account

    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


def update_financed_transaction(
    session: Session,
    transaction_id: int,
    updates: FinancedTransactionUpdateRequest,
) -> Transaction:
    """Modifies an existing financed transaction in-place while maintaining accounting integrity.

    Supports metadata updates, principal amount adjustments, installment term modifications,
    payment method switching (between Credit Cards), and envelope reassignments.
    Reconciled transactions only permit metadata updates (notes, merchant, dates); their
    financial terms and accounts remain locked. Non-financed and reversed transactions
    cannot be modified through this function. If amount is modified, term must also
    be provided.

    Args:
        session: Active SQLModel database session.
        transaction_id: Integer ID of the financed transaction to modify.
        updates: FinancedTransactionUpdateRequest containing fields to update.

    Returns:
        The updated and refreshed Transaction instance.

    Raises:
        ValueError: If transaction doesn't exist, is not FINANCED, has been reversed,
            is reconciled and financial fields are altered, amount is modified
            without term, payment method is not a Credit Card, or non-positive
            amounts/terms are given.
    """
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise ValueError(f"Transaction with id: {transaction_id} does not exist.")

    if tx.transaction_type != TransactionType.FINANCED:
        raise ValueError(
            "Only financed transactions can be modified through this function."
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
        if updates.amount is not None:
            raise ValueError(
                "Cannot modify amount of a reconciled financed transaction."
            )
        if updates.term is not None:
            raise ValueError(
                "Cannot modify term of a reconciled financed transaction."
            )
        if (
            updates.payment_method_name is not None
            and updates.payment_method_name != tx.account.name
        ):
            raise ValueError(
                "Cannot change the payment method of a reconciled financed transaction."
            )
        if updates.envelope_name is not None:
            raise ValueError(
                "Cannot modify envelope of a reconciled financed transaction."
            )

    # Validations
    if updates.merchant is not None:
        if not updates.merchant.strip():
            raise ValueError("Merchant name cannot be empty.")
        tx.merchant = updates.merchant.strip()

    if updates.amount is not None:
        if updates.amount <= Decimal("0"):
            raise ValueError("Amount financed has to be greater than 0.")
        if updates.term is None:
            raise ValueError(
                "Term must be provided when modifying the financed amount."
            )

    if updates.term is not None:
        if updates.term <= 0:
            raise ValueError("Term has to be a positive number.")

    if updates.logged_date is not None:
        tx.logged_date = updates.logged_date

    if updates.posted_date is not None:
        tx.posted_date = updates.posted_date

    if updates.note is not None:
        tx.note = updates.note

    if updates.is_reconciled is not None:
        tx.is_reconciled = updates.is_reconciled

    # Resolve target payment method
    old_account = tx.account
    target_account = old_account
    if updates.payment_method_name is not None:
        acc = account_repo.get_account_by_name(session, updates.payment_method_name)
        if not acc:
            raise ValueError(f"Account {updates.payment_method_name} does not exist.")
        if acc.account_type != AccountType.CREDIT_CARD:
            raise ValueError("Account type has to be credit card.")
        target_account = acc

    # Resolve envelope
    if not tx.splits:
        raise ValueError(f"Transaction #{transaction_id} has no envelope splits.")
    first_split = tx.splits[0]
    if not first_split.envelope:
        raise ValueError(f"Envelope for transaction #{transaction_id} not found.")
    current_envelope = first_split.envelope

    target_envelope = current_envelope
    if updates.envelope_name is not None and updates.envelope_name.strip():
        target_envelope = envelope_repo.get_or_create_envelope(
            session, EnvelopeBase(name=updates.envelope_name.strip())
        )

    # Calculate amounts and term note
    old_amount = calculate_transaction_total(tx)
    new_amount = updates.amount if updates.amount is not None else old_amount

    if updates.term is not None:
        monthly_payment = round(new_amount / Decimal(updates.term), 2)
        target_envelope.note = f"{monthly_payment}/mo."
        session.add(target_envelope)

    # Bind target account if changed
    if target_account != old_account:
        tx.account = target_account

    # Update envelope splits in place
    if new_amount != old_amount or target_envelope != current_envelope:
        for split in tx.splits:
            split.envelope = target_envelope
            if split.amount > Decimal("0"):
                split.amount = new_amount
            else:
                split.amount = -1 * new_amount
            session.add(split)

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
modify_financed_transaction = update_financed_transaction