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


class TestGetTransactions:
    @pytest.fixture
    def populated_db(self, session):
        """Sets up accounts, envelopes, and a variety of transactions across dates and types."""
        today = date.today()
        current_year = today.year
        current_month = today.month

        # Accounts
        cash = get_or_create_account(session, "Cash", AccountType.CASH)
        cash.current_balance += Decimal("5000")
        session.add(cash)

        visa = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        session.add(visa)

        # Envelopes
        groceries = get_or_create_envelope(session, "Groceries")
        fun = get_or_create_envelope(session, "Fun")
        utilities = get_or_create_envelope(session, "Utilities")
        cc_envelope = get_or_create_envelope(session, "Credit Card Payment")
        unassigned = get_or_create_envelope(session, "Unassigned")
        session.commit()

        # 1. Income on 5th of system month
        income_tx = envelope_service.add_to_cash(
            session, amount=Decimal("1500"), source="Paycheck", note="Biweekly salary"
        )
        income_tx.logged_date = date(current_year, current_month, 5)
        session.add(income_tx)

        # 2. Cash split expense on 10th of system month (Walmart: $20 Fun + $20 Groceries = $40)
        walmart_split = TransactionRequest(
            merchant="Walmart",
            logged_date=date(current_year, current_month, 10),
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-20"), envelope_name="Fun"),
                LedgerRequest(amount=Decimal("-20"), envelope_name="Groceries"),
            ],
            note="Groceries and snacks",
        )
        walmart_tx = transaction_service.add_reg_transaction(session, walmart_split)

        # 3. Credit Card split expense on 15th of system month (Target: $30 Groceries + $70 Fun = $100)
        target_split = TransactionRequest(
            merchant="Target",
            logged_date=date(current_year, current_month, 15),
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-30"), envelope_name="Groceries"),
                LedgerRequest(amount=Decimal("-70"), envelope_name="Fun"),
            ],
            note="Home supplies & games",
        )
        target_tx = transaction_service.add_reg_transaction(session, target_split)

        # 4. Financed transaction on 20th of system month ($1200 Apple Store)
        financed_req = FinancedTransaction(
            merchant="Apple Store",
            logged_date=date(current_year, current_month, 20),
            term=12,
            amount=Decimal("1200"),
            envelope_name=None,
            payment_method_name="Visa",
            note="MacBook Air",
        )
        financed_tx = transaction_service.add_financed_transaction(session, financed_req)

        # 5. Envelope transfer on 22nd of system month ($50 from Fun to Utilities)
        # Fund Unassigned first, transfer to Fun so Fun has positive balance
        envelope_service.add_to_cash(session, Decimal("500"), "Fund Income")
        envelope_service.assign_to_envelope(
            session, destination="Fun", amount=Decimal("200")
        )
        transfer_res = envelope_service.transfer_between_envelopes(
            session, source="Fun", destination="Utilities", amount=Decimal("50")
        )
        transfer_tx = transfer_res.transfer_transaction
        transfer_tx.logged_date = date(current_year, current_month, 22)
        session.add(transfer_tx)



        # 6. Out-of-default-range transactions:
        # Early transaction on 1st of month (before 3rd)
        early_req = TransactionRequest(
            merchant="Early Coffee",
            logged_date=date(current_year, current_month, 1),
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-5"), envelope_name="Fun")
            ],
        )
        early_tx = transaction_service.add_reg_transaction(session, early_req)

        # Late transaction on 29th of month (after 28th)
        late_req = TransactionRequest(
            merchant="Late Dinner",
            logged_date=date(current_year, current_month, 29),
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-45"), envelope_name="Fun")
            ],
        )
        late_tx = transaction_service.add_reg_transaction(session, late_req)

        session.commit()
        return {
            "cash": cash,
            "visa": visa,
            "groceries": groceries,
            "fun": fun,
            "utilities": utilities,
            "walmart_tx": walmart_tx,
            "target_tx": target_tx,
            "financed_tx": financed_tx,
            "transfer_tx": transfer_tx,
            "income_tx": income_tx,
            "early_tx": early_tx,
            "late_tx": late_tx,
        }

    def test_default_fetch_filters_transfers_and_date_range(self, session, populated_db):
        """Default fetch should exclude transfers and only return transactions between 3rd and 28th."""
        results = transaction_service.get_transactions(session)

        merchants = [tx.merchant for tx in results]
        # In default date range (3rd to 28th):
        # 5th (Paycheck - INCOME), 10th (Walmart - EXPENSE), 15th (Target - EXPENSE), 20th (Apple Store - FINANCED),
        # Fund Fun (INCOME).
        # Transfers (22nd) and out-of-range (1st, 29th) should NOT be in results.
        assert "Walmart" in merchants
        assert "Target" in merchants
        assert "Apple Store" in merchants
        assert "Paycheck" in merchants
        assert "Early Coffee" not in merchants
        assert "Late Dinner" not in merchants
        assert not any(tx.transaction_type == TransactionType.TRANSFER for tx in results)

    def test_split_cash_transaction_total(self, session, populated_db):
        """Split cash transaction ($20 Fun + $20 Groceries) should report total $40."""
        results = transaction_service.get_transactions(
            session,
            date_from=date(date.today().year, date.today().month, 10),
            date_to=date(date.today().year, date.today().month, 10),
        )
        assert len(results) == 1
        walmart = results[0]
        assert walmart.merchant == "Walmart"
        assert walmart.total == Decimal("40")
        assert walmart.total_amount == Decimal("40")
        assert walmart.payment_method_name == "Cash"

    def test_credit_card_balancing_entry_excluded_from_total(self, session, populated_db):
        """CC transaction ($30 + $70) should report total $100, filtering out balancing entry (+100)."""
        results = transaction_service.get_transactions(
            session,
            date_from=date(date.today().year, date.today().month, 15),
            date_to=date(date.today().year, date.today().month, 15),
        )
        assert len(results) == 1
        target = results[0]
        assert target.merchant == "Target"
        assert target.total == Decimal("100")
        assert target.payment_method_name == "Visa"

    def test_financed_transaction_positive_total(self, session, populated_db):
        """Financed transaction (+1200, -1200) should report positive financed total $1200."""
        results = transaction_service.get_transactions(
            session,
            date_from=date(date.today().year, date.today().month, 20),
            date_to=date(date.today().year, date.today().month, 20),
        )
        assert len(results) == 1
        apple = results[0]
        assert apple.merchant == "Apple Store"
        assert apple.total == Decimal("1200")
        assert apple.transaction_type == TransactionType.FINANCED

    def test_filter_by_envelope(self, session, populated_db):
        """Filtering by envelope name returns all transactions touching that envelope."""
        # Both Walmart ($20) and Target ($30) used Groceries
        results = transaction_service.get_transactions(
            session, envelope="Groceries"
        )
        merchants = [tx.merchant for tx in results]
        assert "Walmart" in merchants
        assert "Target" in merchants
        assert "Apple Store" not in merchants

    def test_filter_by_cc_payment_envelope_excludes_balancing_entries(self, session, populated_db):
        """Filtering by 'Credit Card Payment' envelope should NOT return regular CC expense transactions."""
        results = transaction_service.get_transactions(
            session, envelope="Credit Card Payment"
        )
        merchants = [tx.merchant for tx in results]
        assert "Target" not in merchants

    def test_filter_by_account(self, session, populated_db):
        """Filtering by account string name returns only transactions using that payment method."""
        cash_results = transaction_service.get_transactions(session, account="Cash")
        assert all(tx.payment_method_name == "Cash" for tx in cash_results)

        visa_results = transaction_service.get_transactions(session, account="Visa")
        assert all(tx.payment_method_name == "Visa" for tx in visa_results)
        visa_merchants = [tx.merchant for tx in visa_results]
        assert "Target" in visa_merchants
        assert "Apple Store" in visa_merchants
        assert "Walmart" not in visa_merchants

    def test_filter_by_custom_date_range(self, session, populated_db):
        """Passing custom date_from and date_to captures transactions including early and late ones."""
        today = date.today()
        all_results = transaction_service.get_transactions(
            session,
            date_from=date(today.year, today.month, 1),
            date_to=date(today.year, today.month, 31 if today.month in [1, 3, 5, 7, 8, 10, 12] else 30),
        )
        merchants = [tx.merchant for tx in all_results]
        assert "Early Coffee" in merchants
        assert "Late Dinner" in merchants

    def test_filter_by_limit(self, session, populated_db):
        """Limit parameter caps the number of returned transactions."""
        results = transaction_service.get_transactions(session, limit=2)
        assert len(results) == 2

    def test_explicit_transfer_transaction_type(self, session, populated_db):
        """When transaction_type=TransactionType.TRANSFER is requested, transfers are returned."""
        results = transaction_service.get_transactions(
            session, transaction_type=TransactionType.TRANSFER
        )
        assert len(results) >= 1
        assert all(tx.transaction_type == TransactionType.TRANSFER for tx in results)
        totals = {tx.total for tx in results}
        assert Decimal("50") in totals or Decimal("200") in totals


    def test_filter_by_multiple_transaction_types(self, session, populated_db):
        """Passing a list of transaction types from enum filters accurately."""
        results = transaction_service.get_transactions(
            session,
            transaction_type=[TransactionType.EXPENSE, TransactionType.TRANSFER],
        )
        types = {tx.transaction_type for tx in results}
        assert TransactionType.EXPENSE in types
        assert TransactionType.TRANSFER in types
        assert TransactionType.INCOME not in types

    def test_alias_get_transaction_and_fetch_transactions(self, session, populated_db):
        """get_transaction and fetch_transactions aliases produce the exact same results as get_transactions."""
        res1 = transaction_service.get_transactions(session)
        res2 = transaction_service.get_transaction(session)
        res3 = transaction_service.fetch_transactions(session)
        assert [r.id for r in res1] == [r.id for r in res2] == [r.id for r in res3]

    def test_invalid_limit_raises_error(self, session):
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            transaction_service.get_transactions(session, limit=0)

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            transaction_service.get_transactions(session, limit=-5)

    def test_invalid_date_range_raises_error(self, session):
        with pytest.raises(ValueError, match="cannot be after date_to"):
            transaction_service.get_transactions(
                session,
                date_from=date(2026, 5, 20),
                date_to=date(2026, 5, 10),
            )

    def test_nonexistent_envelope_raises_error(self, session):
        with pytest.raises(ValueError, match="Envelope 'GhostEnvelope' does not exist"):
            transaction_service.get_transactions(session, envelope="GhostEnvelope")

        with pytest.raises(ValueError, match="Envelope must be a string"):
            transaction_service.get_transactions(session, envelope=123)

    def test_nonexistent_account_raises_error(self, session):
        with pytest.raises(ValueError, match="Account 'GhostAccount' does not exist"):
            transaction_service.get_transactions(session, account="GhostAccount")

        with pytest.raises(ValueError, match="Account must be a string"):
            transaction_service.get_transactions(session, account=123)

    def test_invalid_transaction_type_raises_error(self, session):
        with pytest.raises(ValueError, match="Invalid transaction type"):
            transaction_service.get_transactions(session, transaction_type="INVALID_TYPE")

    def test_sorting_order_descending(self, session, populated_db):
        """Transactions should be returned in descending order by logged_date."""
        results = transaction_service.get_transactions(
            session,
            date_from=date(date.today().year, date.today().month, 1),
            date_to=date(date.today().year, date.today().month, 28),
        )
        dates = [tx.logged_date for tx in results]
        assert dates == sorted(dates, reverse=True)

    def test_camel_case_transaction_type(self, session, populated_db):
        """Passing transactionType keyword argument works."""
        results = transaction_service.get_transactions(
            session, transactionType=TransactionType.FINANCED
        )
        assert len(results) == 1
        assert results[0].merchant == "Apple Store"
        assert results[0].transaction_type == TransactionType.FINANCED

    def test_envelope_and_account_filtering(self, session, populated_db):
        """Filtering with both envelope and account string names simultaneously."""
        results = transaction_service.get_transactions(
            session, envelope="Groceries", account="Visa"
        )
        assert len(results) == 1
        assert results[0].merchant == "Target"
        assert results[0].total == Decimal("100")



