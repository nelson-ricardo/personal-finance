from decimal import Decimal
import pytest
from budget_app.repositories import envelope_repo
from budget_app.schemas import (
    AccountBase,
    AccountType,
    AccountUpdate,
    EnvelopeBase,
    EnvelopeSplitRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service, envelope_service, transaction_service


class TestCreateAccount:
    def test_create_account_success(self, session):
        acc_info = AccountBase(
            name="Savings",
            account_type=AccountType.CASH,
            current_balance=Decimal("500"),
        )
        account = account_service.create_account(session, acc_info)

        assert account is not None
        assert account.id is not None
        assert account.name == "Savings"
        assert account.account_type == AccountType.CASH
        assert account.current_balance == Decimal("500")

    def test_create_account_empty_name_raises_error(self, session):
        acc_info = AccountBase(
            name="   ",
            account_type=AccountType.CASH,
        )
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            account_service.create_account(session, acc_info)

    def test_create_account_duplicate_name_raises_error(self, session):
        acc_info = AccountBase(
            name="Checking",
            account_type=AccountType.CASH,
        )
        account_service.create_account(session, acc_info)

        duplicate = AccountBase(
            name="Checking",
            account_type=AccountType.CASH,
        )
        with pytest.raises(ValueError, match="Account 'Checking' already exists"):
            account_service.create_account(session, duplicate)

    def test_create_cash_account_negative_balance_raises_error(self, session):
        acc_info = AccountBase(
            name="CashNegative",
            account_type=AccountType.CASH,
            current_balance=Decimal("-100"),
        )
        with pytest.raises(ValueError, match="Cash account balance cannot be negative"):
            account_service.create_account(session, acc_info)

    def test_create_cash_account_clears_credit_fields(self, session):
        acc_info = AccountBase(
            name="CashWithCreditFields",
            account_type=AccountType.CASH,
            current_balance=Decimal("200"),
            total_statement_balance=Decimal("100"),
            monthly_payment=Decimal("50"),
        )
        account = account_service.create_account(session, acc_info)
        assert account.total_statement_balance is None
        assert account.monthly_payment is None

    def test_create_credit_card_auto_links_envelope(self, session):
        acc_info = AccountBase(
            name="Visa Rewards",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("0"),
        )
        account = account_service.create_account(session, acc_info)
        assert account is not None
        assert account.envelope_id is not None
        assert account.envelope is not None
        assert account.envelope.name == "Credit Card Payment"

    def test_create_credit_card_negative_balance_raises_error(self, session):
        acc_info = AccountBase(
            name="BadCard",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-50"),
        )
        with pytest.raises(ValueError, match="Balance cannot be negative"):
            account_service.create_account(session, acc_info)


class TestStartingBalanceAndDerivedBalance:
    def test_cash_starting_balance_creates_income_transaction(self, session):
        acc = account_service.create_account(
            session,
            AccountBase(name="Chase Checking", account_type=AccountType.CASH, current_balance=Decimal("1500")),
        )
        assert acc.current_balance == Decimal("1500")
        assert account_service.get_account_balance(session, "Chase Checking") == Decimal("1500")

        # Unassigned envelope should have received the funds
        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        assert unassigned is not None
        assert envelope_repo.get_balance_for_envelope(session, unassigned) >= Decimal("1500")

    def test_debt_starting_balance_creates_adjustment_transaction(self, session):
        acc = account_service.create_account(
            session,
            AccountBase(name="Auto Loan", account_type=AccountType.LOAN, current_balance=Decimal("12000")),
        )
        assert acc.current_balance == Decimal("12000")
        assert account_service.get_account_balance(session, "Auto Loan") == Decimal("12000")

        # Account Adjustment envelope should have received the split
        adj = envelope_repo.get_envelope_by_name(session, "Account Adjustment")
        assert adj is not None
        assert envelope_repo.get_balance_for_envelope(session, adj) >= Decimal("12000")

    def test_get_all_accounts_returns_derived_balances(self, session):
        account_service.create_account(
            session,
            AccountBase(name="Bank A", account_type=AccountType.CASH, current_balance=Decimal("300")),
        )
        account_service.create_account(
            session,
            AccountBase(name="Card B", account_type=AccountType.CREDIT_CARD, current_balance=Decimal("200")),
        )
        all_accs = account_service.get_all_accounts(session)
        acc_dict = {a.name: a.current_balance for a in all_accs}
        assert acc_dict["Bank A"] == Decimal("300")
        assert acc_dict["Card B"] == Decimal("200")


class TestInterestAdjustments:
    def test_add_interest_charge_credit_card(self, session):
        card = account_service.create_account(
            session,
            AccountBase(name="Discover", account_type=AccountType.CREDIT_CARD, current_balance=Decimal("500")),
        )
        assert card.current_balance == Decimal("500")

        tx = account_service.add_interest_charge(
            session, account_name="Discover", amount=Decimal("15.50"), note="Monthly interest fee"
        )
        assert tx is not None
        assert tx.transaction_type == "INTEREST_CHARGE"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope.name == "Account Adjustment"

        # Derived debt balance should have increased by $15.50
        assert account_service.get_account_balance(session, "Discover") == Decimal("515.50")
        assert card.current_balance == Decimal("515.50")

    def test_add_interest_charge_on_cash_raises_error(self, session):
        account_service.create_account(
            session, AccountBase(name="MyCash", account_type=AccountType.CASH)
        )
        with pytest.raises(ValueError, match="Interest charges can only be applied to debt accounts"):
            account_service.add_interest_charge(session, "MyCash", Decimal("10.00"))

    def test_add_interest_charge_negative_amount_raises_error(self, session):
        account_service.create_account(
            session, AccountBase(name="MyDebt", account_type=AccountType.LOAN)
        )
        with pytest.raises(ValueError, match="Interest charge amount must be greater than 0"):
            account_service.add_interest_charge(session, "MyDebt", Decimal("-5.00"))

    def test_add_interest_charge_nonexistent_account_raises_error(self, session):
        with pytest.raises(ValueError, match="Account 'GhostBank' does not exist"):
            account_service.add_interest_charge(session, "GhostBank", Decimal("20.00"))

    def test_add_interest_earned_cash(self, session):
        savings = account_service.create_account(
            session,
            AccountBase(name="High Yield Savings", account_type=AccountType.CASH, current_balance=Decimal("1000")),
        )
        assert savings.current_balance == Decimal("1000")

        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        unassigned_bal_before = envelope_repo.get_balance_for_envelope(session, unassigned)

        tx = account_service.add_interest_earned(
            session, account_name="High Yield Savings", amount=Decimal("4.25"), note="APY payout"
        )
        assert tx is not None
        assert tx.transaction_type == "INTEREST_EARNED"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope.name == "Unassigned"

        # Derived cash balance should increase by $4.25
        assert account_service.get_account_balance(session, "High Yield Savings") == Decimal("1004.25")
        assert savings.current_balance == Decimal("1004.25")

        # Unassigned envelope should have also increased by $4.25
        unassigned_bal_after = envelope_repo.get_balance_for_envelope(session, unassigned)
        assert unassigned_bal_after == unassigned_bal_before + Decimal("4.25")

    def test_add_interest_earned_on_debt_raises_error(self, session):
        account_service.create_account(
            session, AccountBase(name="DebtCard", account_type=AccountType.CREDIT_CARD)
        )
        with pytest.raises(ValueError, match="Interest earned can only be applied to Cash/Savings accounts"):
            account_service.add_interest_earned(session, "DebtCard", Decimal("10.00"))

    def test_add_interest_earned_negative_amount_raises_error(self, session):
        account_service.create_account(
            session, AccountBase(name="CheckingAcct", account_type=AccountType.CASH)
        )
        with pytest.raises(ValueError, match="Interest earned amount must be greater than 0"):
            account_service.add_interest_earned(session, "CheckingAcct", Decimal("-1.00"))


class TestAccountLifecycleAndFiltering:
    def test_delete_account_no_transactions_success(self, session):
        account_service.create_account(
            session,
            AccountBase(name="OldChecking", account_type=AccountType.CASH),
        )
        deleted = account_service.delete_account(session, "OldChecking")
        assert deleted.is_active is False

        # By default, get_all_accounts filters for active accounts only
        active_accounts = account_service.get_all_accounts(session)
        assert "OldChecking" not in [a.name for a in active_accounts]

        # Explicitly fetching inactive accounts
        inactive_accounts = account_service.get_all_accounts(session, is_active=False)
        assert "OldChecking" in [a.name for a in inactive_accounts]

        # Fetching all accounts regardless of active status
        all_accounts = account_service.get_all_accounts(session, is_active=None)
        assert "OldChecking" in [a.name for a in all_accounts]

    def test_delete_account_with_starting_balance_success(self, session):
        account_service.create_account(
            session,
            AccountBase(
                name="InitialDebt",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("250.00"),
            ),
        )
        deleted = account_service.delete_account(session, "InitialDebt")
        assert deleted.is_active is False
        assert deleted.name == "InitialDebt"

    def test_delete_account_with_expense_transaction_raises_error(self, session):
        envelope_service.create_envelope(session, EnvelopeBase(name="Dining"))
        account_service.create_account(
            session,
            AccountBase(name="SpendCard", account_type=AccountType.CREDIT_CARD),
        )
        tx_req = TransactionRequest(
            merchant="Restaurant",
            payment_method_name="SpendCard",
            transaction_type=TransactionType.EXPENSE,
            splits=[
                EnvelopeSplitRequest(
                    amount=Decimal("-40.00"), envelope_name="Dining"
                )
            ],
        )
        transaction_service.add_reg_transaction(session, tx_req)

        with pytest.raises(
            ValueError,
            match="Cannot delete account 'SpendCard' with associated transactions",
        ):
            account_service.delete_account(session, "SpendCard")

    def test_delete_account_with_interest_charge_raises_error(self, session):
        account_service.create_account(
            session,
            AccountBase(name="InterestLoan", account_type=AccountType.LOAN),
        )
        account_service.add_interest_charge(
            session, "InterestLoan", Decimal("15.00")
        )

        with pytest.raises(
            ValueError,
            match="Cannot delete account 'InterestLoan' with associated transactions",
        ):
            account_service.delete_account(session, "InterestLoan")

    def test_delete_default_cash_raises_error(self, session):
        with pytest.raises(
            ValueError,
            match="Cannot delete or archive the default 'Cash' account",
        ):
            account_service.delete_account(session, "Cash")

    def test_delete_nonexistent_account_raises_error(self, session):
        with pytest.raises(ValueError, match="Account 'GhostBank' does not exist"):
            account_service.delete_account(session, "GhostBank")

    def test_activate_account(self, session):
        account_service.create_account(
            session,
            AccountBase(name="DormantChecking", account_type=AccountType.CASH),
        )
        account_service.delete_account(session, "DormantChecking")
        dormant = account_service.get_account(
            session, "DormantChecking", is_active=True
        )
        assert dormant is None

        reactivated = account_service.activate_account(session, "DormantChecking")
        assert reactivated.is_active is True
        active_dormant = account_service.get_account(
            session, "DormantChecking", is_active=True
        )
        assert active_dormant is not None

    def test_update_account_name(self, session):
        account_service.create_account(
            session,
            AccountBase(name="OldName", account_type=AccountType.CASH),
        )
        updated = account_service.update_account(
            session,
            target_name="OldName",
            account_info=AccountUpdate(name="NewName"),
        )
        assert updated.name == "NewName"
        assert account_service.get_account(session, "NewName") is not None
        assert account_service.get_account(session, "OldName") is None

    def test_update_account_rename_cash_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Cannot rename the default 'Cash' account"
        ):
            account_service.update_account(
                session,
                target_name="Cash",
                account_info=AccountUpdate(name="PhysicalCash"),
            )

    def test_update_account_deactivate_via_is_active_flag(self, session):
        account_service.create_account(
            session,
            AccountBase(name="FlagTest", account_type=AccountType.CASH),
        )
        updated = account_service.update_account(
            session,
            target_name="FlagTest",
            account_info=AccountUpdate(is_active=False),
        )
        assert updated.is_active is False
        active_names = [a.name for a in account_service.get_all_accounts(session)]
        assert "FlagTest" not in active_names
