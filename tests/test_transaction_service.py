from datetime import date
from decimal import Decimal
import pytest

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories import account_repo, envelope_repo, transaction_repo
from budget_app.schemas import (
    AccountBase,
    AccountType,
    EnvelopeBase,
    FinancedTransaction,
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

    test_envelope1 = get_or_create_envelope(session, "Groceries")
    test_envelope2 = get_or_create_envelope(session, "Fun")

    session.flush()
    env1_addition = LedgerRequest(
        amount=Decimal("500"), envelope_name="Groceries"
    )
    env2_addition = LedgerRequest(
        amount=Decimal("500"), envelope_name="Fun"
    )

    tx = TransactionRequest(
        merchant="Testing",
        note="Testing purposes only",
        payment_method_name="Cash",
        transaction_type=TransactionType.INCOME,
        ledger_entries=[env1_addition, env2_addition],
    )
    master_tx = transaction_repo.create_transaction(session, tx)
    session.flush()
    session.refresh(master_tx)
    session.refresh(cash_account)
    return (master_tx, cash_account)


class TestAddRegTransaction:
    def test_single_entry_cash(self, session, transaction_set_up):
        og_tx, cash_account = transaction_set_up

        ledger_entry = LedgerRequest(
            amount=Decimal("-50"), envelope_name="Groceries"
        )
        tx_req = TransactionRequest(
            merchant="Groceries",
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

    def test_mult_entry_cash(self, session, transaction_set_up):
        og_tx, cash_account = transaction_set_up

        entry1 = LedgerRequest(amount=Decimal("-60"), envelope_name="Groceries")
        entry2 = LedgerRequest(amount=Decimal("-40"), envelope_name="Fun")

        tx_req = TransactionRequest(
            merchant="Target",
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

    def test_single_entry_cc(self, session, transaction_set_up):
        get_or_create_envelope(session, "Credit Card Payment")
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry = LedgerRequest(amount=Decimal("-75"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Supermarket",
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )

        test_transaction = transaction_service.add_reg_transaction(session, tx_req)

        assert test_transaction is not None
        assert test_transaction.account.name == "Visa"
        assert len(test_transaction.entries) == 2
        assert cc_account.current_balance == Decimal("75")

    def test_mult_entry_cc(self, session, transaction_set_up):
        get_or_create_envelope(session, "Credit Card Payment")
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry1 = LedgerRequest(amount=Decimal("-100"), envelope_name="Groceries")
        entry2 = LedgerRequest(amount=Decimal("-50"), envelope_name="Fun")
        tx_req = TransactionRequest(
            merchant="Department Store",
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry1, entry2],
        )

        test_transaction = transaction_service.add_reg_transaction(session, tx_req)

        assert test_transaction is not None
        assert test_transaction.account.name == "Visa"
        assert len(test_transaction.entries) == 3
        assert cc_account.current_balance == Decimal("150")

    def test_no_account_raises_error(self, session):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Unknown",
            payment_method_name="NonExistentAccount",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )

        with pytest.raises(ValueError):
            transaction_service.add_reg_transaction(session, tx_req)

    def test_no_envelope_raises_error(self, session, transaction_set_up):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="NonExistentEnvelope")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )

        with pytest.raises(ValueError):
            transaction_service.add_reg_transaction(session, tx_req)

    def test_is_financed_type_raises_error(self, session, transaction_set_up):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.FINANCED,
            ledger_entries=[entry],
        )

        with pytest.raises(
            ValueError,
            match="financed transaction should be processed through add_financed_transaction",
        ):
            transaction_service.add_reg_transaction(session, tx_req)


class TestAddFinancedTransaction:
    def test_success_default_envelope(self, session):
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        initial_balance = cc_account.current_balance

        financed_tx = FinancedTransaction(
            merchant="Apple Store",
            term=12,
            amount=Decimal("1200"),
            envelope_name=None,
            payment_method_name="Visa",
            note="MacBook purchase",
        )

        result = transaction_service.add_financed_transaction(session, financed_tx)

        assert result is not None
        assert result.merchant == "Apple Store"
        assert result.transaction_type == TransactionType.FINANCED
        assert result.account.name == "Visa"
        assert len(result.entries) == 2

        amounts = [e.amount for e in result.entries]
        assert Decimal("1200") in amounts
        assert Decimal("-1200") in amounts

        env = envelope_repo.get_envelope_by_name(session, "Apple Store - 12")
        assert env is not None
        assert env.note == "100.00/mo."

        session.refresh(cc_account)
        assert cc_account.current_balance == initial_balance + Decimal("1200")

    def test_success_custom_envelope(self, session):
        cc_account = get_or_create_account(session, "Mastercard", AccountType.CREDIT_CARD)
        initial_balance = cc_account.current_balance

        financed_tx = FinancedTransaction(
            merchant="Best Buy",
            term=24,
            amount=Decimal("2400"),
            envelope_name="Home Appliance Finance",
            payment_method_name="Mastercard",
            note="Fridge",
        )

        result = transaction_service.add_financed_transaction(session, financed_tx)

        assert result is not None
        assert result.merchant == "Best Buy"
        assert len(result.entries) == 2

        env = envelope_repo.get_envelope_by_name(session, "Home Appliance Finance")
        assert env is not None
        assert env.note == "100.00/mo."

        session.refresh(cc_account)
        assert cc_account.current_balance == initial_balance + Decimal("2400")

    def test_existing_envelope(self, session):
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        get_or_create_envelope(session, "Furniture")

        financed_tx = FinancedTransaction(
            merchant="IKEA",
            term=6,
            amount=Decimal("600"),
            envelope_name="Furniture",
            payment_method_name="Visa",
        )

        result = transaction_service.add_financed_transaction(session, financed_tx)
        assert result is not None
        env = envelope_repo.get_envelope_by_name(session, "Furniture")
        assert env is not None

    def test_term_zero_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=0,
            amount=Decimal("500"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        with pytest.raises(ValueError, match="Term has to be a positive number"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_term_negative_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=-5,
            amount=Decimal("500"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        with pytest.raises(ValueError, match="Term has to be a positive number"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_nonexistent_account_raises_error(self, session):
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=12,
            amount=Decimal("500"),
            envelope_name=None,
            payment_method_name="GhostCard",
        )

        with pytest.raises(ValueError, match="Account GhostCard does not exist"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_non_credit_card_raises_error(self, session):
        get_or_create_account(session, "CashAccount", AccountType.CASH)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=12,
            amount=Decimal("500"),
            envelope_name=None,
            payment_method_name="CashAccount",
        )

        with pytest.raises(ValueError, match="Account type has to be credit card"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_amount_zero_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=12,
            amount=Decimal("0"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        with pytest.raises(ValueError, match="Amount financed has to be greater than 0"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_amount_negative_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=12,
            amount=Decimal("-100"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        with pytest.raises(ValueError, match="Amount financed has to be greater than 0"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_empty_merchant_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="   ",
            term=12,
            amount=Decimal("500"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        with pytest.raises(ValueError, match="Merchant name cannot be empty"):
            transaction_service.add_financed_transaction(session, financed_tx)

    def test_preserves_dates_and_reconciled(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        test_date = date(2026, 1, 15)
        financed_tx = FinancedTransaction(
            merchant="Apple",
            logged_date=test_date,
            posted_date=test_date,
            is_reconciled=True,
            term=12,
            amount=Decimal("1200"),
            envelope_name=None,
            payment_method_name="Visa",
        )

        result = transaction_service.add_financed_transaction(session, financed_tx)
        assert result.logged_date == test_date
        assert result.posted_date == test_date
        assert result.is_reconciled is True

    def test_monthly_payment_rounding(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = FinancedTransaction(
            merchant="Store",
            term=3,
            amount=Decimal("100"),
            envelope_name="Test Rounding",
            payment_method_name="Visa",
        )

        transaction_service.add_financed_transaction(session, financed_tx)
        env = envelope_repo.get_envelope_by_name(session, "Test Rounding")
        assert env is not None
        assert env.note == "33.33/mo."
