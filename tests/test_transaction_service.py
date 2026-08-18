from decimal import Decimal
import pytest

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories import account_repo, envelope_repo, transaction_repo
from budget_app.schemas import (
    AccountBase,
    AccountType,
    EnvelopeBase,
    LedgerRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service, envelope_service, transaction_service


def get_or_create_envelope(session, name: str) -> Envelope:
    env = envelope_repo.get_envelope_by_name(session, name)
    if not env:
        env = envelope_service.create_envelope(session, EnvelopeBase(name=name))
    return env


def get_or_create_account(session, name: str, account_type: AccountType) -> Account:
    acc = account_repo.get_account_by_name(session, name)
    if not acc:
        acc = account_service.create_account(
            session, AccountBase(name=name, account_type=account_type)
        )
    return acc


@pytest.fixture
def transaction_set_up(session):
    """
    Fixture to set up envelopes and cash account so they are ready for transactions
    """
    cash_account = get_or_create_account(session, "Cash", AccountType.CASH)
    cash_account.current_balance += Decimal("1000")
    session.add(cash_account)

    # create some envelopes
    test_envelope1 = get_or_create_envelope(session, "Groceries")
    test_envelope2 = get_or_create_envelope(session, "Fun")

    session.flush()
    # create a transaction to add money to those envelopes
    env1_addition = LedgerRequest(
        amount=Decimal("500"), envelope_name="Groceries"
    )
    env2_addition = LedgerRequest(
        amount=Decimal("500"), envelope_name="Fun"
    )

    tx = TransactionRequest(
        merchant="Testing",
        note="Testing purposes only",
        is_financed=False,
        payment_method_name="Cash",
        transaction_type=TransactionType.INCOME,
        ledger_entries=[env1_addition, env2_addition],
    )
    master_tx = transaction_repo.create_transaction(session, tx)
    session.flush()
    session.refresh(master_tx)
    session.refresh(cash_account)
    return (master_tx, cash_account)


def test_add_reg_transaction_single_entry_cash(session, transaction_set_up):
    og_tx, cash_account = transaction_set_up

    ledger_entry = LedgerRequest(
        amount=Decimal("-50"), envelope_name="Groceries"
    )
    tx_req = TransactionRequest(
        merchant="Groceries",
        is_financed=False,
        payment_method_name="Cash",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[ledger_entry],
    )
    test_transaction: Transaction = transaction_service.add_reg_transaction(
        session, tx_req
    )

    assert test_transaction is not None
    assert test_transaction.account.name == "Cash"
    assert len(test_transaction.entries) == 1
    assert cash_account.current_balance == Decimal("950")
    assert test_transaction.entries[0].amount == Decimal("-50")
    assert test_transaction.entries[0].envelope is not None
    assert test_transaction.entries[0].envelope.name == "Groceries"


def test_add_reg_transaction_mult_entry_cash(session, transaction_set_up):
    og_tx, cash_account = transaction_set_up

    entry1 = LedgerRequest(amount=Decimal("-60"), envelope_name="Groceries")
    entry2 = LedgerRequest(amount=Decimal("-40"), envelope_name="Fun")

    tx_req = TransactionRequest(
        merchant="Target",
        is_financed=False,
        payment_method_name="Cash",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[entry1, entry2],
    )

    test_transaction = transaction_service.add_reg_transaction(session, tx_req)

    assert test_transaction is not None
    assert test_transaction.account.name == "Cash"
    assert len(test_transaction.entries) == 2
    assert cash_account.current_balance == Decimal("900")
    assert {e.envelope.name for e in test_transaction.entries if e.envelope} == {
        "Groceries",
        "Fun",
    }


def test_add_reg_transaction_single_entry_cc(session, transaction_set_up):
    get_or_create_envelope(session, "Credit Card Payment")
    cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

    entry = LedgerRequest(amount=Decimal("-75"), envelope_name="Groceries")
    tx_req = TransactionRequest(
        merchant="Supermarket",
        is_financed=False,
        payment_method_name="Visa",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[entry],
    )

    test_transaction = transaction_service.add_reg_transaction(session, tx_req)

    assert test_transaction is not None
    assert test_transaction.account.name == "Visa"
    assert len(test_transaction.entries) == 2
    assert cc_account.current_balance == Decimal("75")


def test_add_reg_transaction_mult_entry_cc(session, transaction_set_up):
    get_or_create_envelope(session, "Credit Card Payment")
    cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

    entry1 = LedgerRequest(amount=Decimal("-100"), envelope_name="Groceries")
    entry2 = LedgerRequest(amount=Decimal("-50"), envelope_name="Fun")
    tx_req = TransactionRequest(
        merchant="Department Store",
        is_financed=False,
        payment_method_name="Visa",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[entry1, entry2],
    )

    test_transaction = transaction_service.add_reg_transaction(session, tx_req)

    assert test_transaction is not None
    assert test_transaction.account.name == "Visa"
    assert len(test_transaction.entries) == 3
    assert cc_account.current_balance == Decimal("150")


def test_add_reg_transaction_no_acc(session):
    entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
    tx_req = TransactionRequest(
        merchant="Unknown",
        is_financed=False,
        payment_method_name="NonExistentAccount",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[entry],
    )

    with pytest.raises(ValueError):
        transaction_service.add_reg_transaction(session, tx_req)


def test_add_reg_tranaction_no_env(session, transaction_set_up):
    entry = LedgerRequest(amount=Decimal("-50"), envelope_name="NonExistentEnvelope")
    tx_req = TransactionRequest(
        merchant="Store",
        is_financed=False,
        payment_method_name="Cash",
        transaction_type=TransactionType.EXPENSE,
        ledger_entries=[entry],
    )

    with pytest.raises(ValueError):
        transaction_service.add_reg_transaction(session, tx_req)
