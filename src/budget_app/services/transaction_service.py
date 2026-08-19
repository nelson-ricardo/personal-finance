from decimal import Decimal

from sqlmodel import Session

from budget_app.models import Account, Transaction
from budget_app.schemas import EnvelopeBase
from budget_app.repositories import (
    account_repo,
    ledger_repo,
    transaction_repo,
    envelope_repo,
)
from budget_app.schemas import (
    AccountType, 
    LedgerRequest, 
    TransactionRequest,
    FinancedTransaction,
    TransactionType
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