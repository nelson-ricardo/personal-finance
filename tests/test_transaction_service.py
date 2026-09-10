from datetime import date
from decimal import Decimal

import pytest

from budget_app.models import Account, Envelope, EnvelopeSplit, Transaction
from budget_app.repositories import (
    account_repo,
    envelope_repo,
    envelope_split_repo,
    transaction_repo,
)
from budget_app.schemas import (
    AccountBase,
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    EnvelopeSplitResponse,
    FinancedTransaction,
    FinancedTransactionUpdateRequest,
    LedgerRequest,
    TransactionDetailResponse,
    TransactionRequest,
    TransactionType,
    TransactionUpdateRequest,
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

    get_or_create_envelope(session, "Groceries")
    get_or_create_envelope(session, "Fun")

    session.flush()
    env1_addition = LedgerRequest(amount=Decimal("500"), envelope_name="Groceries")
    env2_addition = LedgerRequest(amount=Decimal("500"), envelope_name="Fun")

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

        ledger_entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
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
        entry = LedgerRequest(
            amount=Decimal("-50"), envelope_name="NonExistentEnvelope"
        )
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
            match="financed transaction should be processed",
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
        cc_account = get_or_create_account(
            session, "Mastercard", AccountType.CREDIT_CARD
        )
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
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
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

        with pytest.raises(
            ValueError, match="Amount financed has to be greater than 0"
        ):
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

        with pytest.raises(
            ValueError, match="Amount financed has to be greater than 0"
        ):
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
        """Sets up accounts, envelopes, and transactions across dates and types."""
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
        get_or_create_envelope(session, "Credit Card Payment")
        get_or_create_envelope(session, "Unassigned")
        session.commit()

        # 1. Income on 5th of system month
        income_tx = envelope_service.add_to_cash(
            session, amount=Decimal("1500"), source="Paycheck", note="Biweekly salary"
        )
        income_tx.logged_date = date(current_year, current_month, 5)
        session.add(income_tx)

        # 2. Cash split on 10th (Walmart: $20 Fun + $20 Groceries = $40)
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

        # 3. Credit Card split on 15th (Target: $30 Groceries + $70 Fun = $100)
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
        financed_tx = transaction_service.add_financed_transaction(
            session, financed_req
        )

        # 5. Envelope transfer on 22nd of system month ($50 from Fun to Utilities)
        # Fund Unassigned first, transfer to Fun so Fun has positive balance
        fund_tx = envelope_service.add_to_cash(session, Decimal("500"), "Fund Income")
        fund_tx.logged_date = date(current_year, current_month, 22)
        session.add(fund_tx)
        session.commit()
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
            ledger_entries=[LedgerRequest(amount=Decimal("-5"), envelope_name="Fun")],
        )
        early_tx = transaction_service.add_reg_transaction(session, early_req)

        # Late transaction on 29th of month (after 28th)
        late_req = TransactionRequest(
            merchant="Late Dinner",
            logged_date=date(current_year, current_month, 29),
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[LedgerRequest(amount=Decimal("-45"), envelope_name="Fun")],
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

    def test_default_fetch_filters_transfers_and_date_range(
        self, session, populated_db
    ):
        """Default fetch excludes transfers and limits dates to 3rd through 28th."""
        results = transaction_service.get_transactions(session)

        merchants = [tx.merchant for tx in results]
        # In default date range (3rd to 28th):
        # 5th (Paycheck), 10th (Walmart), 15th (Target), 20th (Apple Store)
        # Transfers (22nd) and out-of-range (1st, 29th) should NOT be in results.
        assert "Walmart" in merchants
        assert "Target" in merchants
        assert "Apple Store" in merchants
        assert "Paycheck" in merchants
        assert "Early Coffee" not in merchants
        assert "Late Dinner" not in merchants
        assert not any(
            tx.transaction_type == TransactionType.TRANSFER for tx in results
        )

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

    def test_credit_card_balancing_entry_excluded_from_total(
        self, session, populated_db
    ):
        """CC tx ($30 + $70) reports total $100, filtering out balancing entry."""
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
        """Financed tx (+1200, -1200) reports positive financed total $1200."""
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
        """Filtering by envelope returns all transactions touching that envelope."""
        # Both Walmart ($20) and Target ($30) used Groceries
        results = transaction_service.get_transactions(session, envelope="Groceries")
        merchants = [tx.merchant for tx in results]
        assert "Walmart" in merchants
        assert "Target" in merchants
        assert "Apple Store" not in merchants

    def test_filter_by_cc_payment_envelope_excludes_balancing_entries(
        self, session, populated_db
    ):
        """Filtering by CC Payment envelope excludes regular CC expenses."""
        results = transaction_service.get_transactions(
            session, envelope="Credit Card Payment"
        )
        merchants = [tx.merchant for tx in results]
        assert "Target" not in merchants

    def test_filter_by_account(self, session, populated_db):
        """Filtering by account returns only transactions using that payment method."""
        cash_results = transaction_service.get_transactions(session, account="Cash")
        assert all(tx.payment_method_name == "Cash" for tx in cash_results)

        visa_results = transaction_service.get_transactions(session, account="Visa")
        assert all(tx.payment_method_name == "Visa" for tx in visa_results)
        visa_merchants = [tx.merchant for tx in visa_results]
        assert "Target" in visa_merchants
        assert "Apple Store" in visa_merchants
        assert "Walmart" not in visa_merchants

    def test_filter_by_custom_date_range(self, session, populated_db):
        """Custom date_from and date_to captures transactions including out-of-range."""
        today = date.today()
        all_results = transaction_service.get_transactions(
            session,
            date_from=date(today.year, today.month, 1),
            date_to=date(
                today.year,
                today.month,
                31 if today.month in [1, 3, 5, 7, 8, 10, 12] else 30,
            ),
        )
        merchants = [tx.merchant for tx in all_results]
        assert "Early Coffee" in merchants
        assert "Late Dinner" in merchants

    def test_filter_by_limit(self, session, populated_db):
        """Limit parameter caps the number of returned transactions."""
        results = transaction_service.get_transactions(session, limit=2)
        assert len(results) == 2

    def test_explicit_transfer_transaction_type(self, session, populated_db):
        """When transaction_type=TRANSFER is requested, transfers are returned."""
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
        """Aliases produce the exact same results as get_transactions."""
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
            transaction_service.get_transactions(session, envelope=123)  # type: ignore

    def test_nonexistent_account_raises_error(self, session):
        with pytest.raises(ValueError, match="Account 'GhostAccount' does not exist"):
            transaction_service.get_transactions(session, account="GhostAccount")

        with pytest.raises(ValueError, match="Account must be a string"):
            transaction_service.get_transactions(session, account=123)  # type: ignore

    def test_invalid_transaction_type_raises_error(self, session):
        with pytest.raises(ValueError, match="Invalid transaction type"):
            transaction_service.get_transactions(
                session,
                transaction_type="INVALID_TYPE",  # type: ignore
            )

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


class TestDeleteTransaction:
    def test_reverse_cash_expense(self, session):
        # 1. Add income and allocate to Groceries
        envelope_service.add_to_cash(session, Decimal("500"), "Income")
        groceries = envelope_service.create_envelope(
            session, EnvelopeBase(name="Groceries")
        )
        envelope_service.assign_to_envelope(
            session, destination="Groceries", amount=Decimal("200")
        )

        # Cash balance = 500, Groceries balance = 200
        cash = account_repo.get_account_by_name(session, "Cash")
        assert cash is not None
        assert cash.current_balance == Decimal("500")
        assert envelope_repo.get_balance_for_envelope(session, groceries) == Decimal(
            "200"
        )

        # 2. Make an expense of $50 from Groceries
        expense_req = TransactionRequest(
            merchant="Trader Joe's",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
            ],
        )
        tx = transaction_service.add_reg_transaction(session, expense_req)
        session.refresh(cash)
        assert cash.current_balance == Decimal("450")
        assert envelope_repo.get_balance_for_envelope(session, groceries) == Decimal(
            "150"
        )

        # 3. Delete / Reverse the transaction
        assert tx.id is not None
        rev_tx = transaction_service.delete_transaction(session, tx.id)

        assert rev_tx is not None
        assert rev_tx.transaction_type == TransactionType.REVERSAL
        assert rev_tx.merchant == "Reversal: Trader Joe's"
        assert len(rev_tx.entries) == 1
        assert rev_tx.entries[0].amount == Decimal("50")  # Inverted

        # Balances restored
        session.refresh(cash)
        assert cash.current_balance == Decimal("500")
        assert envelope_repo.get_balance_for_envelope(session, groceries) == Decimal(
            "200"
        )

        # Original transaction note updated
        session.refresh(tx)
        assert tx.note is not None and "[REVERSED]" in tx.note

    def test_reverse_credit_card_expense(self, session):
        # 1. Create Credit Card and Dining envelope
        visa = account_service.create_account(
            session, AccountBase(name="Visa", account_type=AccountType.CREDIT_CARD)
        )
        dining = envelope_service.create_envelope(session, EnvelopeBase(name="Dining"))
        envelope_service.add_to_cash(session, Decimal("500"), "Income")
        envelope_service.assign_to_envelope(
            session, destination="Dining", amount=Decimal("150")
        )

        cc_payment_env = envelope_repo.get_envelope_by_name(
            session, "Credit Card Payment"
        )
        assert cc_payment_env is not None

        # 2. Spend $60 on Visa from Dining
        expense_req = TransactionRequest(
            merchant="Chipotle",
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-60"), envelope_name="Dining")
            ],
        )
        tx = transaction_service.add_reg_transaction(session, expense_req)

        session.refresh(visa)
        assert visa.current_balance == Decimal("60")
        assert envelope_repo.get_balance_for_envelope(session, dining) == Decimal("90")
        assert envelope_repo.get_balance_for_envelope(
            session, cc_payment_env
        ) == Decimal("60")

        # 3. Reverse the credit card expense
        assert tx.id is not None
        rev_tx = transaction_service.delete_transaction(session, tx.id)

        assert rev_tx.transaction_type == TransactionType.REVERSAL
        session.refresh(visa)
        assert visa.current_balance == Decimal("0")  # Debt removed
        assert envelope_repo.get_balance_for_envelope(session, dining) == Decimal(
            "150"
        )  # Dining restored
        assert envelope_repo.get_balance_for_envelope(
            session, cc_payment_env
        ) == Decimal("0")  # CC payment reduced

    def test_reverse_income_transaction(self, session):
        # 1. Add income
        income_tx = envelope_service.add_to_cash(session, Decimal("1000"), "Paycheck")
        cash = account_repo.get_account_by_name(session, "Cash")
        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        assert cash is not None
        assert unassigned is not None

        assert cash.current_balance == Decimal("1000")
        assert envelope_repo.get_balance_for_envelope(session, unassigned) == Decimal(
            "1000"
        )

        # 2. Reverse the income transaction
        assert income_tx.id is not None
        transaction_service.delete_transaction(session, income_tx.id)

        session.refresh(cash)
        assert cash.current_balance == Decimal("0")  # Income deducted from cash
        assert envelope_repo.get_balance_for_envelope(session, unassigned) == Decimal(
            "0"
        )

    def test_reverse_financed_transaction(self, session):
        # 1. Create Credit Card and Financed transaction
        visa = account_service.create_account(
            session, AccountBase(name="Visa", account_type=AccountType.CREDIT_CARD)
        )
        financed_req = FinancedTransaction(
            merchant="Apple",
            amount=Decimal("1200"),
            term=12,
            payment_method_name="Visa",
            envelope_name="MacBook",
        )
        financed_tx = transaction_service.add_financed_transaction(
            session, financed_req
        )

        session.refresh(visa)
        assert visa.current_balance == Decimal("1200")

        # 2. Reverse the financed transaction
        assert financed_tx.id is not None
        rev_tx = transaction_service.delete_transaction(session, financed_tx.id)

        session.refresh(visa)
        assert visa.current_balance == Decimal("0")  # Financed debt cleared
        assert rev_tx.transaction_type == TransactionType.REVERSAL

    def test_reverse_already_reversed_raises_error(self, session):
        envelope_service.add_to_cash(session, Decimal("200"), "Income")
        envelope_service.create_envelope(session, EnvelopeBase(name="Groceries"))
        envelope_service.assign_to_envelope(
            session, destination="Groceries", amount=Decimal("100")
        )

        expense_req = TransactionRequest(
            merchant="Market",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-40"), envelope_name="Groceries")
            ],
        )
        tx = transaction_service.add_reg_transaction(session, expense_req)

        # First reversal succeeds
        assert tx.id is not None
        rev_tx = transaction_service.delete_transaction(session, tx.id)

        # Attempting to reverse the original transaction again fails
        with pytest.raises(ValueError, match="has already been reversed"):
            transaction_service.delete_transaction(session, tx.id)

        # Attempting to reverse the reversal transaction itself fails
        assert rev_tx.id is not None
        with pytest.raises(ValueError, match="has already been reversed"):
            transaction_service.delete_transaction(session, rev_tx.id)

    def test_reverse_nonexistent_transaction_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Transaction with id: 99999 does not exist"
        ):
            transaction_service.delete_transaction(session, 99999)

    def test_reversal_filtered_in_get_transactions(self, session):
        # Create an expense and reverse it
        envelope_service.add_to_cash(session, Decimal("300"), "Income")
        envelope_service.create_envelope(session, EnvelopeBase(name="Groceries"))
        envelope_service.assign_to_envelope(
            session, destination="Groceries", amount=Decimal("100")
        )

        expense_req = TransactionRequest(
            merchant="Costco",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
            ],
        )
        tx = transaction_service.add_reg_transaction(session, expense_req)
        assert tx.id is not None
        rev_tx = transaction_service.delete_transaction(session, tx.id)

        # 1. Exclude both REVERSAL transaction and reversed transaction
        default_results = transaction_service.get_transactions(session)
        assert not any(
            t.transaction_type == TransactionType.REVERSAL for t in default_results
        )
        assert not any(t.id == tx.id for t in default_results)
        assert not any(t.id == rev_tx.id for t in default_results)

        # 2. Explicit request for REVERSAL should return the reversal transaction
        reversal_results = transaction_service.get_transactions(
            session, transaction_type=TransactionType.REVERSAL
        )
        assert any(t.id == rev_tx.id for t in reversal_results)
        assert all(
            t.transaction_type == TransactionType.REVERSAL for t in reversal_results
        )

        # 3. include_reversed=True should include the reversed transaction
        all_results = transaction_service.get_transactions(
            session, include_reversed=True
        )
        assert any(t.id == tx.id for t in all_results)


class TestGetTransactionById:
    def test_get_single_split_cash_transaction_details(self, session):
        # 1. Setup Cash and envelopes
        envelope_service.add_to_cash(session, Decimal("500"), "Income")
        groceries = envelope_service.create_envelope(
            session, EnvelopeBase(name="Groceries")
        )
        fun = envelope_service.create_envelope(session, EnvelopeBase(name="Fun"))
        envelope_service.assign_to_envelope(
            session, destination="Groceries", amount=Decimal("100")
        )
        envelope_service.assign_to_envelope(
            session, destination="Fun", amount=Decimal("100")
        )

        # 2. Create a split expense ($30 Groceries, $20 Fun)
        split_req = TransactionRequest(
            merchant="Walmart",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            note="Weekly split shopping",
            ledger_entries=[
                LedgerRequest(amount=Decimal("-30"), envelope_name="Groceries"),
                LedgerRequest(amount=Decimal("-20"), envelope_name="Fun"),
            ],
        )
        tx = transaction_service.add_reg_transaction(session, split_req)

        # 3. Fetch transaction detail by ID
        assert tx.id is not None
        detail = transaction_service.get_transaction_by_id(session, tx.id)

        assert detail is not None
        assert detail.id == tx.id
        assert detail.merchant == "Walmart"
        assert detail.note == "Weekly split shopping"
        assert detail.payment_method_name == "Cash"
        assert detail.account_name == "Cash"
        assert detail.transaction_type == TransactionType.EXPENSE
        assert detail.total == Decimal("50")
        assert detail.total_amount == Decimal("50")

        # Verify child ledger entries
        assert len(detail.entries) == 2
        assert len(detail.ledger_entries) == 2

        entry_map = {e.envelope_name: e.amount for e in detail.entries}
        assert entry_map["Groceries"] == Decimal("-30")
        assert entry_map["Fun"] == Decimal("-20")

        # Verify envelope IDs
        for e in detail.entries:
            if e.envelope_name == "Groceries":
                assert e.envelope_id == groceries.id
            elif e.envelope_name == "Fun":
                assert e.envelope_id == fun.id

    def test_get_single_credit_card_transaction_details(self, session):
        account_service.create_account(
            session, AccountBase(name="Visa", account_type=AccountType.CREDIT_CARD)
        )
        envelope_service.create_envelope(session, EnvelopeBase(name="Dining"))
        envelope_service.add_to_cash(session, Decimal("500"), "Income")
        envelope_service.assign_to_envelope(
            session, destination="Dining", amount=Decimal("100")
        )

        expense_req = TransactionRequest(
            merchant="Olive Garden",
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[
                LedgerRequest(amount=Decimal("-75"), envelope_name="Dining")
            ],
        )
        tx = transaction_service.add_reg_transaction(session, expense_req)

        assert tx.id is not None
        detail = transaction_service.get_transaction_by_id(session, tx.id)

        assert detail.id == tx.id
        assert detail.payment_method_name == "Visa"
        assert detail.total == Decimal("75")
        # Contains Dining (-75) and Credit Card Payment (+75)
        assert len(detail.entries) == 2
        entry_map = {e.envelope_name: e.amount for e in detail.entries}
        assert entry_map["Dining"] == Decimal("-75")
        assert entry_map["Credit Card Payment"] == Decimal("75")

    def test_get_single_financed_transaction_details(self, session):
        account_service.create_account(
            session, AccountBase(name="Visa", account_type=AccountType.CREDIT_CARD)
        )
        financed_req = FinancedTransaction(
            merchant="Best Buy",
            amount=Decimal("600"),
            term=6,
            payment_method_name="Visa",
            envelope_name="TV Financing",
        )
        financed_tx = transaction_service.add_financed_transaction(
            session, financed_req
        )

        assert financed_tx.id is not None
        detail = transaction_service.get_transaction_by_id(session, financed_tx.id)

        assert detail.id == financed_tx.id
        assert detail.merchant == "Best Buy"
        assert detail.transaction_type == TransactionType.FINANCED
        assert detail.total == Decimal("600")
        assert len(detail.entries) == 2
        amounts = {e.amount for e in detail.entries}
        assert Decimal("600") in amounts
        assert Decimal("-600") in amounts

    def test_aliases_fetch_transaction_by_id_and_detail(self, session):
        envelope_service.add_to_cash(session, Decimal("100"), "Cash Gift")
        cash = account_repo.get_account_by_name(session, "Cash")
        assert cash is not None and cash.transactions
        income = cash.transactions[0]
        assert income.id is not None

        res1 = transaction_service.get_transaction_by_id(session, income.id)
        res2 = transaction_service.fetch_transaction_by_id(session, income.id)
        res3 = transaction_service.get_transaction_detail(session, income.id)

        assert res1.id == res2.id == res3.id
        assert res1.merchant == res2.merchant == res3.merchant
        assert len(res1.entries) == len(res2.entries) == len(res3.entries)

    def test_get_nonexistent_transaction_by_id_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Transaction with id: 99999 does not exist"
        ):
            transaction_service.get_transaction_by_id(session, 99999)


class TestUpdateTransaction:
    def test_update_metadata_only(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Safeway",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert cash_account.current_balance == Decimal("950")

        # Update merchant, note, and logged_date
        new_date = date(2026, 8, 15)
        update_req = TransactionUpdateRequest(
            merchant="Safeway Store #123",
            note="Weekly grocery trip",
            logged_date=new_date,
        )
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        assert updated_tx.id == tx.id
        assert updated_tx.merchant == "Safeway Store #123"
        assert updated_tx.note == "Weekly grocery trip"
        assert updated_tx.logged_date == new_date
        # Balance and ledger remain intact
        assert cash_account.current_balance == Decimal("950")
        assert len(updated_tx.entries) == 1
        assert updated_tx.entries[0].amount == Decimal("-50")

    def test_reconciled_metadata_allowed(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Trader Joe's",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            is_reconciled=True,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.is_reconciled is True

        update_req = TransactionUpdateRequest(
            merchant="Trader Joe's #456",
            note="Reconciled receipt verified",
        )
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        assert updated_tx.merchant == "Trader Joe's #456"
        assert updated_tx.note == "Reconciled receipt verified"
        assert updated_tx.is_reconciled is True

    def test_reconciled_ledger_entries_blocked(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Trader Joe's",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            is_reconciled=True,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        new_entry = LedgerRequest(amount=Decimal("-60"), envelope_name="Groceries")
        update_req = TransactionUpdateRequest(ledger_entries=[new_entry])

        assert tx.id is not None
        with pytest.raises(
            ValueError, match="Cannot modify (?:envelope splits|ledger entries) of a reconciled transaction"
        ):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_reconciled_payment_method_blocked(self, session, transaction_set_up):
        get_or_create_envelope(session, "Credit Card Payment")
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Trader Joe's",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            is_reconciled=True,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = TransactionUpdateRequest(payment_method_name="Visa")
        assert tx.id is not None
        with pytest.raises(
            ValueError,
            match="Cannot change the payment method of a reconciled transaction",
        ):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_update_split_amounts_cash(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Costco",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert cash_account.current_balance == Decimal("950")

        # Update expense from $50 to $80
        new_entry = LedgerRequest(amount=Decimal("-80"), envelope_name="Groceries")
        update_req = TransactionUpdateRequest(ledger_entries=[new_entry])
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        assert cash_account.current_balance == Decimal("920")
        assert len(updated_tx.entries) == 1
        assert updated_tx.entries[0].amount == Decimal("-80")
        assert transaction_service.calculate_transaction_total(updated_tx) == Decimal(
            "80"
        )

    def test_update_split_envelope_category(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Cinema",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        groceries_env = envelope_repo.get_envelope_by_name(session, "Groceries")
        fun_env = envelope_repo.get_envelope_by_name(session, "Fun")
        assert groceries_env is not None
        assert fun_env is not None

        # Before update: Groceries had 500 - 50 = 450; Fun had 500
        assert envelope_repo.get_balance_for_envelope(
            session, groceries_env
        ) == Decimal("450")
        assert envelope_repo.get_balance_for_envelope(session, fun_env) == Decimal(
            "500"
        )

        # Update category from Groceries to Fun
        new_entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Fun")
        update_req = TransactionUpdateRequest(ledger_entries=[new_entry])
        assert tx.id is not None
        transaction_service.update_transaction(session, tx.id, update_req)

        # After update: Groceries restored to 500, Fun deducted to 450
        assert envelope_repo.get_balance_for_envelope(
            session, groceries_env
        ) == Decimal("500")
        assert envelope_repo.get_balance_for_envelope(session, fun_env) == Decimal(
            "450"
        )
        assert cash_account.current_balance == Decimal("950")

    def test_update_payment_method_cash_to_credit_card(
        self, session, transaction_set_up
    ):
        _, cash_account = transaction_set_up
        get_or_create_envelope(session, "Credit Card Payment")
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry = LedgerRequest(amount=Decimal("-60"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Supermarket",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        assert cash_account.current_balance == Decimal("940")
        assert cc_account.current_balance == Decimal("0")

        # Update payment method from Cash to Visa
        update_req = TransactionUpdateRequest(payment_method_name="Visa")
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        # Cash balance refunded to 1000, CC balance increases by 60
        assert cash_account.current_balance == Decimal("1000")
        assert cc_account.current_balance == Decimal("60")
        assert updated_tx.account is not None
        assert updated_tx.account.name == "Visa"
        # CC expense has split + balancing entry
        assert len(updated_tx.entries) == 2
        entry_envelopes = {
            e.envelope.name for e in updated_tx.entries if e.envelope is not None
        }
        assert entry_envelopes == {"Groceries", "Credit Card Payment"}

    def test_update_payment_method_credit_card_to_cash(
        self, session, transaction_set_up
    ):
        _, cash_account = transaction_set_up
        get_or_create_envelope(session, "Credit Card Payment")
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry = LedgerRequest(amount=Decimal("-75"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Whole Foods",
            payment_method_name="Visa",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        assert cc_account.current_balance == Decimal("75")
        assert cash_account.current_balance == Decimal("1000")

        # Update payment method from Visa to Cash
        update_req = TransactionUpdateRequest(payment_method_name="Cash")
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        # CC balance reduced back to 0, Cash balance deducted to 925
        assert cc_account.current_balance == Decimal("0")
        assert cash_account.current_balance == Decimal("925")
        assert updated_tx.account is not None
        assert updated_tx.account.name == "Cash"
        # Only 1 entry (balancing entry removed)
        assert len(updated_tx.entries) == 1
        assert updated_tx.entries[0].envelope is not None
        assert updated_tx.entries[0].envelope.name == "Groceries"
        assert updated_tx.entries[0].amount == Decimal("-75")

    def test_update_both_account_and_splits(self, session, transaction_set_up):
        _, cash_account = transaction_set_up
        get_or_create_envelope(session, "Credit Card Payment")
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)

        entry = LedgerRequest(amount=Decimal("-40"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Target",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        # Update to Visa, and split into Groceries (-$30) and Fun (-$20) -> total $50
        update_req = TransactionUpdateRequest(
            merchant="Target Superstore",
            payment_method_name="Visa",
            ledger_entries=[
                LedgerRequest(amount=Decimal("-30"), envelope_name="Groceries"),
                LedgerRequest(amount=Decimal("-20"), envelope_name="Fun"),
            ],
        )
        assert tx.id is not None
        updated_tx = transaction_service.update_transaction(session, tx.id, update_req)

        assert cash_account.current_balance == Decimal("1000")
        assert cc_account.current_balance == Decimal("50")
        assert updated_tx.account is not None
        assert updated_tx.account.name == "Visa"
        assert updated_tx.merchant == "Target Superstore"
        assert len(updated_tx.entries) == 3  # Groceries + Fun + CC Payment balancing
        assert transaction_service.calculate_transaction_total(updated_tx) == Decimal(
            "50"
        )

    def test_update_financed_transaction_raises_error(self, session):
        get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = transaction_service.add_financed_transaction(
            session,
            FinancedTransaction(
                merchant="Apple Store",
                amount=Decimal("1200"),
                term=12,
                payment_method_name="Visa",
            ),
        )

        update_req = TransactionUpdateRequest(merchant="Apple Store New")
        assert financed_tx.id is not None
        with pytest.raises(
            ValueError, match="Financed transactions cannot be modified"
        ):
            transaction_service.update_transaction(session, financed_tx.id, update_req)

    def test_update_reversed_transaction_raises_error(
        self, session, transaction_set_up
    ):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.id is not None
        transaction_service.reverse_transaction(session, tx.id)

        update_req = TransactionUpdateRequest(merchant="New Name")
        with pytest.raises(
            ValueError, match="has been reversed and cannot be modified"
        ):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_update_nonexistent_transaction_raises_error(self, session):
        update_req = TransactionUpdateRequest(merchant="Ghost")
        with pytest.raises(
            ValueError, match="Transaction with id: 99999 does not exist"
        ):
            transaction_service.update_transaction(session, 99999, update_req)

    def test_update_with_empty_merchant_raises_error(self, session, transaction_set_up):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = TransactionUpdateRequest(merchant="   ")
        assert tx.id is not None
        with pytest.raises(ValueError, match="Merchant name cannot be empty"):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_update_with_empty_ledger_entries_raises_error(
        self, session, transaction_set_up
    ):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = TransactionUpdateRequest(ledger_entries=[])
        assert tx.id is not None
        with pytest.raises(
            ValueError, match="Transaction must have at least one (?:envelope split|ledger entry)"
        ):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_update_with_nonexistent_account_raises_error(
        self, session, transaction_set_up
    ):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = TransactionUpdateRequest(payment_method_name="NonExistentBank")
        assert tx.id is not None
        with pytest.raises(ValueError, match="Account NonExistentBank does not exist"):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_update_with_nonexistent_envelope_raises_error(
        self, session, transaction_set_up
    ):
        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        alien_entry = LedgerRequest(amount=Decimal("-50"), envelope_name="AlienBudget")
        update_req = TransactionUpdateRequest(ledger_entries=[alien_entry])
        assert tx.id is not None
        with pytest.raises(ValueError, match="Envelope AlienBudget does not exist"):
            transaction_service.update_transaction(session, tx.id, update_req)

    def test_modify_transaction_alias(self, session, transaction_set_up):
        entry = LedgerRequest(amount=Decimal("-30"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = TransactionUpdateRequest(note="Updated via alias")
        assert tx.id is not None
        updated_tx = transaction_service.modify_transaction(session, tx.id, update_req)
        assert updated_tx.note == "Updated via alias"


class TestUpdateFinancedTransaction:
    @pytest.fixture
    def financed_setup(self, session):
        cc_account = get_or_create_account(session, "Visa", AccountType.CREDIT_CARD)
        financed_tx = transaction_service.add_financed_transaction(
            session,
            FinancedTransaction(
                merchant="Apple Store",
                amount=Decimal("1200"),
                term=12,
                payment_method_name="Visa",
            ),
        )
        return (financed_tx, cc_account)

    def test_update_metadata_only(self, session, financed_setup):
        financed_tx, cc_account = financed_setup
        assert cc_account.current_balance == Decimal("1200")

        new_date = date(2026, 8, 20)
        update_req = FinancedTransactionUpdateRequest(
            merchant="Apple Fifth Ave",
            note="MacBook Pro M3",
            logged_date=new_date,
        )
        updated_tx = transaction_service.update_financed_transaction(
            session, financed_tx.id, update_req
        )

        assert updated_tx.merchant == "Apple Fifth Ave"
        assert updated_tx.note == "MacBook Pro M3"
        assert updated_tx.logged_date == new_date
        assert cc_account.current_balance == Decimal("1200")
        assert transaction_service.calculate_transaction_total(updated_tx) == Decimal(
            "1200"
        )

    def test_update_term_only(self, session, financed_setup):
        financed_tx, cc_account = financed_setup
        envelope = financed_tx.entries[0].envelope
        assert envelope.note == "100.00/mo."

        # Update term from 12 to 24 months
        update_req = FinancedTransactionUpdateRequest(term=24)
        updated_tx = transaction_service.update_financed_transaction(
            session, financed_tx.id, update_req
        )

        # CC balance stays $1200, but monthly payment becomes $50.00
        assert cc_account.current_balance == Decimal("1200")
        session.refresh(envelope)
        assert envelope.note == "50.00/mo."
        assert transaction_service.calculate_transaction_total(updated_tx) == Decimal(
            "1200"
        )

    def test_update_amount_and_term(self, session, financed_setup):
        financed_tx, cc_account = financed_setup
        envelope = financed_tx.entries[0].envelope

        # Update amount to $1800 and term to 18 months ($100/mo)
        update_req = FinancedTransactionUpdateRequest(
            amount=Decimal("1800"),
            term=18,
        )
        updated_tx = transaction_service.update_financed_transaction(
            session, financed_tx.id, update_req
        )

        assert cc_account.current_balance == Decimal("1800")
        session.refresh(envelope)
        assert envelope.note == "100.00/mo."
        assert len(updated_tx.entries) == 2
        amounts = {e.amount for e in updated_tx.entries}
        assert amounts == {Decimal("1800"), Decimal("-1800")}
        assert transaction_service.calculate_transaction_total(updated_tx) == Decimal(
            "1800"
        )

    def test_update_amount_without_term_raises_error(self, session, financed_setup):
        financed_tx, _ = financed_setup

        update_req = FinancedTransactionUpdateRequest(amount=Decimal("1500"))
        with pytest.raises(
            ValueError,
            match="Term must be provided when modifying the financed amount",
        ):
            transaction_service.update_financed_transaction(
                session, financed_tx.id, update_req
            )

    def test_reconciled_metadata_allowed(self, session, financed_setup):
        financed_tx, _ = financed_setup
        financed_tx.is_reconciled = True
        session.add(financed_tx)
        session.commit()

        update_req = FinancedTransactionUpdateRequest(
            merchant="Apple Official",
            note="Verified statement",
        )
        updated_tx = transaction_service.update_financed_transaction(
            session, financed_tx.id, update_req
        )

        assert updated_tx.merchant == "Apple Official"
        assert updated_tx.note == "Verified statement"
        assert updated_tx.is_reconciled is True

    def test_reconciled_financial_fields_blocked(self, session, financed_setup):
        financed_tx, _ = financed_setup
        financed_tx.is_reconciled = True
        session.add(financed_tx)
        session.commit()

        # Amount blocked
        with pytest.raises(
            ValueError,
            match="Cannot modify amount of a reconciled financed transaction",
        ):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(amount=Decimal("1500"), term=15),
            )

        # Term blocked
        with pytest.raises(
            ValueError,
            match="Cannot modify term of a reconciled financed transaction",
        ):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(term=24),
            )

        # Payment method blocked
        get_or_create_account(session, "Mastercard", AccountType.CREDIT_CARD)
        with pytest.raises(
            ValueError,
            match="Cannot change the payment method of a reconciled",
        ):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(payment_method_name="Mastercard"),
            )

        # Envelope blocked
        with pytest.raises(
            ValueError,
            match="Cannot modify envelope of a reconciled financed transaction",
        ):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(envelope_name="New Envelope"),
            )

    def test_update_payment_method_switching_credit_cards(
        self, session, financed_setup
    ):
        financed_tx, visa_account = financed_setup
        mc_account = get_or_create_account(
            session, "Mastercard", AccountType.CREDIT_CARD
        )

        assert visa_account.current_balance == Decimal("1200")
        assert mc_account.current_balance == Decimal("0")

        update_req = FinancedTransactionUpdateRequest(payment_method_name="Mastercard")
        updated_tx = transaction_service.update_financed_transaction(
            session, financed_tx.id, update_req
        )

        # Visa debt cleared, Mastercard takes over the $1200 debt
        assert visa_account.current_balance == Decimal("0")
        assert mc_account.current_balance == Decimal("1200")
        assert updated_tx.account is not None
        assert updated_tx.account.name == "Mastercard"

    def test_update_payment_method_to_cash_raises_error(self, session, financed_setup):
        financed_tx, _ = financed_setup
        get_or_create_account(session, "Cash", AccountType.CASH)

        update_req = FinancedTransactionUpdateRequest(payment_method_name="Cash")
        with pytest.raises(ValueError, match="Account type has to be credit card"):
            transaction_service.update_financed_transaction(
                session, financed_tx.id, update_req
            )

    def test_update_non_financed_transaction_raises_error(self, session):
        cash_account = get_or_create_account(session, "Cash", AccountType.CASH)
        cash_account.current_balance += Decimal("500")
        get_or_create_envelope(session, "Groceries")

        entry = LedgerRequest(amount=Decimal("-50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Grocery Store",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            ledger_entries=[entry],
        )
        reg_tx = transaction_service.add_reg_transaction(session, tx_req)

        update_req = FinancedTransactionUpdateRequest(merchant="New Store")
        assert reg_tx.id is not None
        with pytest.raises(
            ValueError,
            match="Only financed transactions can be modified through this function",
        ):
            transaction_service.update_financed_transaction(
                session, reg_tx.id, update_req
            )

    def test_update_reversed_financed_transaction_raises_error(
        self, session, financed_setup
    ):
        financed_tx, _ = financed_setup
        transaction_service.reverse_transaction(session, financed_tx.id)

        update_req = FinancedTransactionUpdateRequest(merchant="Apple New")
        with pytest.raises(
            ValueError, match="has been reversed and cannot be modified"
        ):
            transaction_service.update_financed_transaction(
                session, financed_tx.id, update_req
            )

    def test_update_nonexistent_transaction_raises_error(self, session):
        update_req = FinancedTransactionUpdateRequest(merchant="Ghost")
        with pytest.raises(
            ValueError, match="Transaction with id: 99999 does not exist"
        ):
            transaction_service.update_financed_transaction(session, 99999, update_req)

    def test_update_invalid_inputs_raises_error(self, session, financed_setup):
        financed_tx, _ = financed_setup

        # Empty merchant
        with pytest.raises(ValueError, match="Merchant name cannot be empty"):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(merchant="   "),
            )

        # Amount <= 0
        with pytest.raises(
            ValueError, match="Amount financed has to be greater than 0"
        ):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(amount=Decimal("-100"), term=10),
            )

        # Term <= 0
        with pytest.raises(ValueError, match="Term has to be a positive number"):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(term=-5),
            )

        # Non-existent account
        with pytest.raises(ValueError, match="Account NonExistentBank does not exist"):
            transaction_service.update_financed_transaction(
                session,
                financed_tx.id,
                FinancedTransactionUpdateRequest(payment_method_name="NonExistentBank"),
            )

    def test_modify_financed_transaction_alias(self, session, financed_setup):
        financed_tx, _ = financed_setup
        update_req = FinancedTransactionUpdateRequest(note="Updated via alias")
        updated_tx = transaction_service.modify_financed_transaction(
            session, financed_tx.id, update_req
        )
        assert updated_tx.note == "Updated via alias"


class TestEnvelopeSplitUbiquitousLanguage:
    """Tests confirming full support for EnvelopeSplit, splits, and backward compatibility."""

    def test_add_transaction_with_splits_and_envelope_split_request(self, session):
        cash = get_or_create_account(session, "Cash", AccountType.CASH)
        envelope_service.add_to_cash(session, Decimal("1000.00"), "Starting Funds")
        env = get_or_create_envelope(session, "Groceries")

        split1 = EnvelopeSplitRequest(amount=Decimal("-45.50"), envelope_name="Groceries")
        tx_req = TransactionRequest(
            merchant="Trader Joe's",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            splits=[split1],
        )

        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.id is not None
        assert len(tx.splits) == 1
        assert len(tx.entries) == 1  # Backward compatibility property
        assert isinstance(tx.splits[0], EnvelopeSplit)
        assert tx.splits[0].amount == Decimal("-45.50")
        assert cash.current_balance == Decimal("954.50")

        # Test Envelope.splits relationship
        session.refresh(env)
        assert len(env.splits) >= 1
        assert len(env.ledger_entries) == len(env.splits)

    def test_get_transaction_by_id_returns_envelope_splits(self, session):
        get_or_create_account(session, "Cash", AccountType.CASH)
        get_or_create_envelope(session, "Dining")
        get_or_create_envelope(session, "Fun")

        tx_req = TransactionRequest(
            merchant="Restaurant",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            splits=[
                EnvelopeSplitRequest(amount=Decimal("-30.00"), envelope_name="Dining"),
                EnvelopeSplitRequest(amount=Decimal("-20.00"), envelope_name="Fun"),
            ],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.id is not None

        detail = transaction_service.get_transaction_by_id(session, tx.id)
        assert isinstance(detail, TransactionDetailResponse)
        assert len(detail.splits) == 2
        assert len(detail.entries) == 2  # Alias
        assert len(detail.ledger_entries) == 2  # Alias
        assert all(isinstance(s, EnvelopeSplitResponse) for s in detail.splits)
        assert detail.total == Decimal("50.00")

    def test_update_transaction_with_splits(self, session):
        cash = get_or_create_account(session, "Cash", AccountType.CASH)
        envelope_service.add_to_cash(session, Decimal("500.00"), "Initial Deposit")
        get_or_create_envelope(session, "Groceries")
        get_or_create_envelope(session, "Dining")

        tx_req = TransactionRequest(
            merchant="Original Merchant",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            splits=[EnvelopeSplitRequest(amount=Decimal("-50.00"), envelope_name="Groceries")],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.id is not None

        # Update using splits
        update_req = TransactionUpdateRequest(
            merchant="Updated Merchant",
            splits=[EnvelopeSplitRequest(amount=Decimal("-80.00"), envelope_name="Dining")],
        )
        updated = transaction_service.update_transaction(session, tx.id, update_req)
        assert updated.merchant == "Updated Merchant"
        assert len(updated.splits) == 1
        assert updated.splits[0].amount == Decimal("-80.00")
        assert updated.splits[0].envelope is not None
        assert updated.splits[0].envelope.name == "Dining"
        assert cash.current_balance == Decimal("420.00")

    def test_delete_transaction_reversal_with_splits(self, session):
        cash = get_or_create_account(session, "Cash", AccountType.CASH)
        envelope_service.add_to_cash(session, Decimal("500.00"), "Initial Deposit")
        get_or_create_envelope(session, "Groceries")

        tx_req = TransactionRequest(
            merchant="Reversible Merchant",
            payment_method_name="Cash",
            transaction_type=TransactionType.EXPENSE,
            splits=[EnvelopeSplitRequest(amount=Decimal("-60.00"), envelope_name="Groceries")],
        )
        tx = transaction_service.add_reg_transaction(session, tx_req)
        assert tx.id is not None

        rev_tx = transaction_service.delete_transaction(session, tx.id)
        assert rev_tx.transaction_type == TransactionType.REVERSAL
        assert len(rev_tx.splits) == 1
        assert rev_tx.splits[0].amount == Decimal("60.00")
        assert cash.current_balance == Decimal("500.00")

    def test_envelope_split_repo_and_envelope_repo_has_splits(self, session):
        env = get_or_create_envelope(session, "Utilities")
        assert env.id is not None
        get_or_create_account(session, "Cash", AccountType.CASH)
        transaction_repo.create_transaction(
            session,
            TransactionRequest(
                merchant="Electric Co",
                payment_method_name="Cash",
                transaction_type=TransactionType.EXPENSE,
                splits=[EnvelopeSplitRequest(amount=Decimal("-100"), envelope_name="Utilities")],
            ),
        )
        assert envelope_repo.has_splits(session, env.id) is True
        assert envelope_repo.has_ledger_entries(session, env.id) is True

        new_split = envelope_split_repo.add_envelope_split(
            session,
            EnvelopeSplitRequest(amount=Decimal("-25.00"), envelope_name="Utilities"),
        )
        assert isinstance(new_split, EnvelopeSplit)
        assert new_split.amount == Decimal("-25.00")
