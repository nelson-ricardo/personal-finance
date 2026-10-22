from decimal import Decimal

import pytest

from budget_app.repositories import account_repo, category_repo, envelope_repo
from budget_app.schemas import (
    AccountBase,
    AccountCreate,
    AccountType,
    AccountUpdate,
    EnvelopeBase,
    EnvelopeCategoryBase,
    EnvelopeSplitRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service, envelope_service, transaction_service


class TestCreateAccount:
    def test_create_credit_card_account_success(self, session):
        acc_info = AccountCreate(
            name="Savings Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("500"),
        )
        account = account_service.create_account(session, acc_info)

        assert account is not None
        assert account.id is not None
        assert account.name == "Savings Card"
        assert account.account_type == AccountType.CREDIT_CARD
        assert account.current_balance == Decimal("500")

    def test_create_investment_account_success(self, session):
        acc_info = AccountCreate(
            name="Vanguard Index",
            account_type=AccountType.INVESTMENT,
            current_balance=Decimal("15000.00"),
            due_date=15,
            monthly_payment=Decimal("100"),
        )
        account = account_service.create_account(session, acc_info)

        assert account is not None
        assert account.id is not None
        assert account.name == "Vanguard Index"
        assert account.account_type == AccountType.INVESTMENT
        assert account.current_balance == Decimal("15000.00")
        assert account.due_date is None
        assert account.monthly_payment is None
        assert (
            account_service.get_account_balance(session, "Vanguard Index")
            == Decimal("15000.00")
        )

    def test_create_second_cash_account_raises_error(self, session):
        acc_info = AccountCreate(
            name="Checking",
            account_type=AccountType.CASH,
            current_balance=Decimal("500"),
        )
        with pytest.raises(ValueError, match="Only a single cash account is allowed"):
            account_service.create_account(session, acc_info)

    def test_create_account_empty_name_raises_error(self, session):
        acc_info = AccountBase(
            name="   ",
            account_type=AccountType.CREDIT_CARD,
        )
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            account_service.create_account(session, acc_info)

    def test_create_account_duplicate_name_raises_error(self, session):
        acc_info = AccountBase(
            name="MyCard",
            account_type=AccountType.CREDIT_CARD,
        )
        account_service.create_account(session, acc_info)

        duplicate = AccountBase(
            name="MyCard",
            account_type=AccountType.CREDIT_CARD,
        )
        with pytest.raises(ValueError, match="Account 'MyCard' already exists"):
            account_service.create_account(session, duplicate)

    def test_create_cash_account_negative_balance_raises_error(self, session):
        acc_info = AccountCreate(
            name="CashNegative",
            account_type=AccountType.CASH,
            current_balance=Decimal("-100"),
        )
        with pytest.raises(ValueError, match="Cash account balance cannot be negative"):
            account_service.create_account(session, acc_info)

    def test_create_cash_account_clears_credit_fields(self, session):
        seeded_cash = account_repo.get_account_by_name(session, "Cash")
        if seeded_cash:
            session.delete(seeded_cash)
            session.flush()

        acc_info = AccountCreate(
            name="Cash",
            account_type=AccountType.CASH,
            current_balance=Decimal("200"),
            total_statement_balance=Decimal("100"),
            monthly_payment=Decimal("50"),
            due_date=15,
        )
        account = account_service.create_account(session, acc_info)
        assert account.total_statement_balance is None
        assert account.monthly_payment is None
        assert account.due_date is None

    def test_create_credit_card_auto_links_envelope(self, session):
        acc_info = AccountCreate(
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
        acc_info = AccountCreate(
            name="BadCard",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-50"),
        )
        with pytest.raises(ValueError, match="Balance cannot be negative"):
            account_service.create_account(session, acc_info)

    def test_create_credit_card_with_due_date_success(self, session):
        acc_info = AccountCreate(
            name="Discover",
            account_type=AccountType.CREDIT_CARD,
            due_date=25,
        )
        account = account_service.create_account(session, acc_info)
        assert account.due_date == 25
        fetched = account_service.get_account(session, "Discover")
        assert fetched.due_date == 25

    def test_create_account_due_date_out_of_bounds_raises_error(self, session):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AccountCreate(
                name="BadDueDateLow",
                account_type=AccountType.CREDIT_CARD,
                due_date=0,
            )
        with pytest.raises(ValidationError):
            AccountCreate(
                name="BadDueDateHigh",
                account_type=AccountType.CREDIT_CARD,
                due_date=32,
            )

    def test_create_loan_account_with_custom_category(self, session):
        cat = category_repo.get_or_create_category(
            session, EnvelopeCategoryBase(name="Debt Obligations", order_index=10)
        )
        session.commit()

        acc = account_service.create_account(
            session,
            AccountCreate(
                name="Custom Cat Car Loan",
                account_type=AccountType.LOAN,
                category_name="Debt Obligations",
            ),
        )
        assert acc.envelope is not None
        assert acc.envelope.name == "Custom Cat Car Loan"
        assert acc.envelope.category_id == cat.id

    def test_create_loan_account_without_category_leaves_uncategorized(self, session):
        acc = account_service.create_account(
            session,
            AccountCreate(
                name="Uncategorized Student Loan",
                account_type=AccountType.LOAN,
            ),
        )
        assert acc.envelope is not None
        assert acc.envelope.name == "Uncategorized Student Loan"
        assert acc.envelope.category_id is None


class TestStartingBalanceAndDerivedBalance:
    def test_cash_starting_balance_creates_income_transaction(self, session):
        seeded_cash = account_repo.get_account_by_name(session, "Cash")
        if seeded_cash:
            session.delete(seeded_cash)
            session.flush()

        acc = account_service.create_account(
            session,
            AccountCreate(name="Cash", account_type=AccountType.CASH, current_balance=Decimal("1500")),
        )
        assert acc.current_balance == Decimal("1500")
        assert account_service.get_account_balance(session, "Cash") == Decimal("1500")

        # Unassigned envelope should have received the funds
        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        assert unassigned is not None
        assert envelope_repo.get_balance_for_envelope(session, unassigned) >= Decimal("1500")

    def test_debt_starting_balance_creates_adjustment_transaction(self, session):
        acc = account_service.create_account(
            session,
            AccountCreate(name="Auto Loan", account_type=AccountType.LOAN, current_balance=Decimal("12000")),
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
            AccountCreate(name="Card A", account_type=AccountType.CREDIT_CARD, current_balance=Decimal("300")),
        )
        account_service.create_account(
            session,
            AccountCreate(name="Card B", account_type=AccountType.CREDIT_CARD, current_balance=Decimal("200")),
        )
        all_accs = account_service.get_all_accounts(session)
        acc_dict = {a.name: a.current_balance for a in all_accs}
        assert acc_dict["Card A"] == Decimal("300")
        assert acc_dict["Card B"] == Decimal("200")
        assert "Cash" in acc_dict


class TestInterestAdjustments:
    def test_add_interest_charge_credit_card(self, session):
        card = account_service.create_account(
            session,
            AccountCreate(name="Discover", account_type=AccountType.CREDIT_CARD, current_balance=Decimal("500")),
        )
        assert card.current_balance == Decimal("500")

        tx = account_service.add_interest_charge(
            session, account_name="Discover", amount=Decimal("15.50"), note="Monthly interest fee"
        )
        assert tx is not None
        assert tx.transaction_type == "INTEREST_CHARGE"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Account Adjustment"

        # Derived debt balance should have increased by $15.50
        assert account_service.get_account_balance(session, "Discover") == Decimal("515.50")
        assert card.current_balance == Decimal("515.50")

    def test_add_interest_charge_on_cash_raises_error(self, session):
        with pytest.raises(ValueError, match="Interest charges can only be applied to debt accounts"):
            account_service.add_interest_charge(session, "Cash", Decimal("10.00"))

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
        cash = account_repo.get_account_by_name(session, "Cash")
        assert cash is not None
        cash_bal_before = cash.current_balance

        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        assert unassigned is not None
        unassigned_bal_before = envelope_repo.get_balance_for_envelope(session, unassigned)

        tx = account_service.add_interest_earned(
            session, account_name="Cash", amount=Decimal("4.25"), note="APY payout"
        )
        assert tx is not None
        assert tx.transaction_type == "INTEREST_EARNED"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Unassigned"

        # Derived cash balance should increase by $4.25
        assert account_service.get_account_balance(session, "Cash") == cash_bal_before + Decimal("4.25")

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
        with pytest.raises(ValueError, match="Interest earned amount must be greater than 0"):
            account_service.add_interest_earned(session, "Cash", Decimal("-1.00"))


class TestAccountLifecycleAndFiltering:
    def test_delete_account_no_transactions_success(self, session):
        account_service.create_account(
            session,
            AccountBase(name="OldCard", account_type=AccountType.CREDIT_CARD),
        )
        deleted = account_service.delete_account(session, "OldCard")
        assert deleted.is_active is False

        # By default, get_all_accounts filters for active accounts only
        active_accounts = account_service.get_all_accounts(session)
        assert "OldCard" not in [a.name for a in active_accounts]

        # Explicitly fetching inactive accounts
        inactive_accounts = account_service.get_all_accounts(session, is_active=False)
        assert "OldCard" in [a.name for a in inactive_accounts]

        # Fetching all accounts regardless of active status
        all_accounts = account_service.get_all_accounts(session, is_active=None)
        assert "OldCard" in [a.name for a in all_accounts]

    def test_delete_account_with_starting_balance_success(self, session):
        account_service.create_account(
            session,
            AccountCreate(
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
            AccountBase(name="DormantCard", account_type=AccountType.CREDIT_CARD),
        )
        account_service.delete_account(session, "DormantCard")
        dormant = account_service.get_account(
            session, "DormantCard", is_active=True
        )
        assert dormant is None

        reactivated = account_service.activate_account(session, "DormantCard")
        assert reactivated.is_active is True
        active_dormant = account_service.get_account(
            session, "DormantCard", is_active=True
        )
        assert active_dormant is not None

    def test_update_account_name(self, session):
        account_service.create_account(
            session,
            AccountBase(name="OldCardName", account_type=AccountType.CREDIT_CARD),
        )
        updated = account_service.update_account(
            session,
            target_name="OldCardName",
            account_info=AccountUpdate(name="NewCardName"),
        )
        assert updated.name == "NewCardName"
        assert account_service.get_account(session, "NewCardName") is not None
        assert account_service.get_account(session, "OldCardName") is None

    def test_update_account_by_id_success(self, session):
        created = account_service.create_account(
            session,
            AccountBase(name="CardById", account_type=AccountType.CREDIT_CARD),
        )
        updated = account_service.update_account(
            session,
            target=created.id,
            account_info=AccountUpdate(name="CardByIdRenamed", monthly_payment=Decimal("50.00")),
        )
        assert updated.id == created.id
        assert updated.name == "CardByIdRenamed"
        assert updated.monthly_payment == Decimal("50.00")

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
            AccountBase(name="FlagTestCard", account_type=AccountType.CREDIT_CARD),
        )
        updated = account_service.update_account(
            session,
            target_name="FlagTestCard",
            account_info=AccountUpdate(is_active=False),
        )
        assert updated.is_active is False
        active_names = [a.name for a in account_service.get_all_accounts(session)]
        assert "FlagTestCard" not in active_names


class TestMakePayment:
    def test_make_payment_credit_card_flow(self, session):
        # 1. Setup Cash account with funds and budget to Credit Card Payment
        cash_bal_before = account_service.get_account_balance(session, "Cash")
        envelope_service.add_to_cash(session, Decimal("1000.00"), "Paycheck")
        envelope_service.assign_to_envelope(
            session, destination="Credit Card Payment", amount=Decimal("200.00")
        )

        # 2. Setup Credit Card with $500 debt
        account_service.create_account(
            session,
            AccountCreate(
                name="ChaseSapphire",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("500.00"),
            ),
        )
        assert (
            account_service.get_account_balance(session, "ChaseSapphire")
            == Decimal("500.00")
        )

        # 3. Make payment of $200
        txs = account_service.make_payment(
            session, target="ChaseSapphire", amount=Decimal("200.00")
        )

        # 4. Assert single transaction returned with multiple splits
        assert len(txs) == 1
        tx = txs[0]

        # Cash outflow transaction with destination account linkage
        assert tx.account is not None
        assert tx.account.name == "Cash"
        assert tx.destination_account_id is not None
        assert tx.transaction_type == TransactionType.EXPENSE
        assert len(tx.splits) == 2
        # Split 1: Credit Card Payment deduction
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Credit Card Payment"
        assert tx.splits[0].amount == Decimal("-200.00")
        # Split 2: Account Adjustment balancing offset
        assert tx.splits[1].envelope is not None
        assert tx.splits[1].envelope.name == "Account Adjustment"
        assert tx.splits[1].amount == Decimal("200.00")

        # 5. Assert updated balances
        # Cash net change: +1000 - 200 = +800
        assert (
            account_service.get_account_balance(session, "Cash")
            == cash_bal_before + Decimal("800.00")
        )
        # Credit card debt decreased from $500 to $300
        assert (
            account_service.get_account_balance(session, "ChaseSapphire")
            == Decimal("300.00")
        )
        # Payment envelope was consumed: 200 - 200 = 0
        cc_env = envelope_repo.get_envelope_by_name(
            session, "Credit Card Payment"
        )
        assert cc_env is not None
        assert (
            envelope_repo.get_balance_for_envelope(session, cc_env)
            == Decimal("0.00")
        )

    def test_make_payment_loan_flow(self, session):
        # 1. Setup Cash account with funds
        cash_bal_before = account_service.get_account_balance(session, "Cash")
        envelope_service.add_to_cash(session, Decimal("2500.00"), "Deposit")

        # 2. Setup Loan (auto-creates a "CarLoan" envelope) with $10,000 debt
        account_service.create_account(
            session,
            AccountCreate(
                name="CarLoan",
                account_type=AccountType.LOAN,
                current_balance=Decimal("10000.00"),
            ),
        )

        # 3. Budget funds into the CarLoan envelope
        envelope_service.assign_to_envelope(
            session, destination="CarLoan", amount=Decimal("450.00")
        )
        car_env = envelope_repo.get_envelope_by_name(session, "CarLoan")
        assert car_env is not None
        assert (
            envelope_repo.get_balance_for_envelope(session, car_env)
            == Decimal("450.00")
        )

        # 4. Make payment of $450
        txs = account_service.make_payment(
            session, target="CarLoan", amount=Decimal("450.00")
        )
        assert len(txs) == 1
        assert len(txs[0].splits) == 2

        # 5. Assert updated balances
        # Cash net change: +2500 - 450 = +2050
        assert (
            account_service.get_account_balance(session, "Cash")
            == cash_bal_before + Decimal("2050.00")
        )
        assert (
            account_service.get_account_balance(session, "CarLoan")
            == Decimal("9550.00")
        )
        assert (
            envelope_repo.get_balance_for_envelope(session, car_env)
            == Decimal("0.00")
        )

    def test_make_payment_investment_transfer_flow(self, session):
        cash_bal_before = account_service.get_account_balance(session, "Cash")
        envelope_service.add_to_cash(session, Decimal("2000.00"), "Paycheck")

        # Create an Investments envelope and assign $600 to it
        envelope_service.create_envelope(
            session, EnvelopeBase(name="Investments")
        )
        envelope_service.assign_to_envelope(
            session, destination="Investments", amount=Decimal("600.00")
        )

        # Create an Investment account with $5,000 initial balance
        account_service.create_account(
            session,
            AccountCreate(
                name="Schwab Index",
                account_type=AccountType.INVESTMENT,
                current_balance=Decimal("5000.00"),
            ),
        )

        # Transfer $600 from Cash to Schwab Index using the Investments envelope
        txs = account_service.make_payment(
            session,
            target="Schwab Index",
            amount=Decimal("600.00"),
            envelope_name="Investments",
        )
        assert len(txs) == 1
        tx = txs[0]
        assert tx.merchant == "Transfer to Schwab Index"
        assert tx.destination_account_id is not None
        assert len(tx.splits) == 2
        assert tx.splits[0].envelope.name == "Investments"
        assert tx.splits[0].amount == Decimal("-600.00")

        # Cash balance net change: +2000 - 600 = +1400
        assert (
            account_service.get_account_balance(session, "Cash")
            == cash_bal_before + Decimal("1400.00")
        )
        # Investment balance increased from $5,000 to $5,600
        assert (
            account_service.get_account_balance(session, "Schwab Index")
            == Decimal("5600.00")
        )
        # Investments envelope was fully consumed
        inv_env = envelope_repo.get_envelope_by_name(session, "Investments")
        assert (
            envelope_repo.get_balance_for_envelope(session, inv_env)
            == Decimal("0.00")
        )

    def test_make_payment_target_not_found_raises_error(self, session):
        with pytest.raises(ValueError, match="account GhostAccount does not exist"):
            account_service.make_payment(
                session, target="GhostAccount", amount=Decimal("100.00")
            )

    def test_make_payment_to_cash_account_raises_error(self, session):
        with pytest.raises(
            ValueError, match="is not a loan, credit card, or investment account"
        ):
            account_service.make_payment(
                session, target="Cash", amount=Decimal("50.00")
            )

    def test_make_payment_negative_amount_raises_error(self, session):
        account_service.create_account(
            session,
            AccountBase(name="VisaCard", account_type=AccountType.CREDIT_CARD),
        )
        with pytest.raises(ValueError, match="positive value"):
            account_service.make_payment(
                session, target="VisaCard", amount=Decimal("-25.00")
            )

    def test_make_payment_zero_amount_raises_error(self, session):
        account_service.create_account(
            session,
            AccountBase(name="MasterCard", account_type=AccountType.CREDIT_CARD),
        )
        with pytest.raises(ValueError, match="positive value"):
            account_service.make_payment(
                session, target="MasterCard", amount=Decimal("0.00")
            )

    def test_make_payment_to_inactive_account_raises_error(self, session):
        account_service.create_account(
            session,
            AccountBase(name="ClosedCard", account_type=AccountType.CREDIT_CARD),
        )
        account_service.delete_account(session, "ClosedCard")

        with pytest.raises(ValueError, match="inactive|archived"):
            account_service.make_payment(
                session, target="ClosedCard", amount=Decimal("50.00")
            )


class TestAdjustAccountBalance:
    def test_adjust_cash_balance_increase(self, session):
        bal_before = account_service.get_account_balance(session, "Cash")
        unassigned = envelope_repo.get_envelope_by_name(session, "Unassigned")
        assert unassigned is not None
        unassigned_bal_before = envelope_repo.get_balance_for_envelope(
            session, unassigned
        )

        target = bal_before + Decimal("150.00")
        tx = account_service.adjust_account_balance(
            session, account_name="Cash", target_balance=target
        )

        assert tx is not None
        assert tx.transaction_type == TransactionType.INCOME
        assert tx.account is not None
        assert tx.account.name == "Cash"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Unassigned"
        assert tx.splits[0].amount == Decimal("150.00")

        # Check balances
        assert account_service.get_account_balance(session, "Cash") == target
        unassigned_bal_after = envelope_repo.get_balance_for_envelope(
            session, unassigned
        )
        assert unassigned_bal_after == unassigned_bal_before + Decimal("150.00")

    def test_adjust_cash_balance_decrease_with_envelope(self, session):
        envelope_service.create_envelope(
            session, EnvelopeBase(name="Miscellaneous")
        )
        envelope_service.add_to_cash(session, Decimal("500.00"), "Initial Deposit")
        envelope_service.assign_to_envelope(
            session, destination="Miscellaneous", amount=Decimal("200.00")
        )
        misc_env = envelope_repo.get_envelope_by_name(session, "Miscellaneous")
        assert misc_env is not None
        assert (
            envelope_repo.get_balance_for_envelope(session, misc_env)
            == Decimal("200.00")
        )

        bal_before = account_service.get_account_balance(session, "Cash")
        target = bal_before - Decimal("75.00")

        tx = account_service.adjust_account_balance(
            session,
            account_name="Cash",
            target_balance=target,
            envelope_name="Miscellaneous",
        )

        assert tx is not None
        assert tx.transaction_type == TransactionType.EXPENSE
        assert tx.account is not None
        assert tx.account.name == "Cash"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Miscellaneous"
        assert tx.splits[0].amount == Decimal("-75.00")

        assert account_service.get_account_balance(session, "Cash") == target
        assert (
            envelope_repo.get_balance_for_envelope(session, misc_env)
            == Decimal("125.00")
        )

    def test_adjust_cash_balance_decrease_without_envelope_raises_error(
        self, session
    ):
        bal_before = account_service.get_account_balance(session, "Cash")
        with pytest.raises(
            ValueError,
            match="Cash reduction must specify an envelope to deduct funds from",
        ):
            account_service.adjust_account_balance(
                session,
                account_name="Cash",
                target_balance=bal_before - Decimal("50.00"),
            )

    def test_adjust_cash_balance_decrease_with_account_adjustment_raises_error(
        self, session
    ):
        bal_before = account_service.get_account_balance(session, "Cash")
        with pytest.raises(
            ValueError,
            match="Cash reduction cannot be absorbed by 'Account Adjustment'",
        ):
            account_service.adjust_account_balance(
                session,
                account_name="Cash",
                target_balance=bal_before - Decimal("50.00"),
                envelope_name="Account Adjustment",
            )

    def test_adjust_credit_card_debt_increase(self, session):
        account_service.create_account(
            session,
            AccountCreate(
                name="AdjustCardA",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("400.00"),
            ),
        )
        assert (
            account_service.get_account_balance(session, "AdjustCardA")
            == Decimal("400.00")
        )

        # Debt increases from $400 to $460 (more debt owed)
        tx = account_service.adjust_account_balance(
            session,
            account_name="AdjustCardA",
            target_balance=Decimal("460.00"),
        )

        assert tx is not None
        assert tx.transaction_type == TransactionType.INTEREST_CHARGE
        assert tx.account is not None
        assert tx.account.name == "AdjustCardA"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Account Adjustment"
        assert tx.splits[0].amount == Decimal("60.00")

        assert (
            account_service.get_account_balance(session, "AdjustCardA")
            == Decimal("460.00")
        )

    def test_adjust_credit_card_debt_decrease(self, session):
        account_service.create_account(
            session,
            AccountCreate(
                name="AdjustCardB",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("500.00"),
            ),
        )
        assert (
            account_service.get_account_balance(session, "AdjustCardB")
            == Decimal("500.00")
        )

        # Debt decreases from $500 to $420 (less debt owed)
        tx = account_service.adjust_account_balance(
            session,
            account_name="AdjustCardB",
            target_balance=Decimal("420.00"),
        )

        assert tx is not None
        assert tx.transaction_type == TransactionType.INCOME
        assert tx.account is not None
        assert tx.account.name == "AdjustCardB"
        assert len(tx.splits) == 1
        assert tx.splits[0].envelope is not None
        assert tx.splits[0].envelope.name == "Account Adjustment"
        assert tx.splits[0].amount == Decimal("80.00")

        assert (
            account_service.get_account_balance(session, "AdjustCardB")
            == Decimal("420.00")
        )

    def test_adjust_loan_debt_adjustments(self, session):
        account_service.create_account(
            session,
            AccountCreate(
                name="StudentLoanA",
                account_type=AccountType.LOAN,
                current_balance=Decimal("8000.00"),
            ),
        )

        # Debt increases to $8100
        tx_up = account_service.adjust_account_balance(
            session,
            account_name="StudentLoanA",
            target_balance=Decimal("8100.00"),
        )
        assert tx_up is not None
        assert tx_up.transaction_type == TransactionType.INTEREST_CHARGE
        assert (
            account_service.get_account_balance(session, "StudentLoanA")
            == Decimal("8100.00")
        )

        # Debt decreases to $7900
        tx_down = account_service.adjust_account_balance(
            session,
            account_name="StudentLoanA",
            target_balance=Decimal("7900.00"),
        )
        assert tx_down is not None
        assert tx_down.transaction_type == TransactionType.INCOME
        assert (
            account_service.get_account_balance(session, "StudentLoanA")
            == Decimal("7900.00")
        )

    def test_adjust_balance_identical_returns_none(self, session):
        account_service.create_account(
            session,
            AccountCreate(
                name="SyncCard",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("250.00"),
            ),
        )

        result = account_service.adjust_account_balance(
            session, account_name="SyncCard", target_balance=Decimal("250.00")
        )
        assert result is None
        assert (
            account_service.get_account_balance(session, "SyncCard")
            == Decimal("250.00")
        )

    def test_adjust_balance_inactive_account_raises_error(self, session):
        account_service.create_account(
            session,
            AccountBase(
                name="InactiveAdjust", account_type=AccountType.CREDIT_CARD
            ),
        )
        account_service.delete_account(session, "InactiveAdjust")

        with pytest.raises(ValueError, match="inactive|archived"):
            account_service.adjust_account_balance(
                session,
                account_name="InactiveAdjust",
                target_balance=Decimal("100.00"),
            )

    def test_adjust_balance_nonexistent_account_raises_error(self, session):
        with pytest.raises(ValueError, match="does not exist"):
            account_service.adjust_account_balance(
                session,
                account_name="FakeAccount",
                target_balance=Decimal("100.00"),
            )

    def test_adjust_investment_balance_gain_and_loss(self, session):
        # Create an investment account starting at $10,000
        account_service.create_account(
            session,
            AccountCreate(
                name="Fidelity Brokerage",
                account_type=AccountType.INVESTMENT,
                current_balance=Decimal("10000.00"),
            ),
        )
        assert (
            account_service.get_account_balance(session, "Fidelity Brokerage")
            == Decimal("10000.00")
        )

        # 1. Market gain: Adjust up to $10,800 (+800 gain)
        tx_gain = account_service.adjust_account_balance(
            session,
            account_name="Fidelity Brokerage",
            target_balance=Decimal("10800.00"),
        )
        assert tx_gain is not None
        assert tx_gain.transaction_type == TransactionType.INCOME
        assert len(tx_gain.splits) == 1
        assert tx_gain.splits[0].amount == Decimal("800.00")
        assert tx_gain.splits[0].envelope is not None
        assert tx_gain.splits[0].envelope.name == "Account Adjustment"
        assert (
            account_service.get_account_balance(session, "Fidelity Brokerage")
            == Decimal("10800.00")
        )

        # 2. Market drop: Adjust down to $9,500 (-1300 drop)
        tx_loss = account_service.adjust_account_balance(
            session,
            account_name="Fidelity Brokerage",
            target_balance=Decimal("9500.00"),
        )
        assert tx_loss is not None
        assert tx_loss.transaction_type == TransactionType.EXPENSE
        assert len(tx_loss.splits) == 1
        assert tx_loss.splits[0].amount == Decimal("-1300.00")
        assert tx_loss.splits[0].envelope is not None
        assert tx_loss.splits[0].envelope.name == "Account Adjustment"
        assert (
            account_service.get_account_balance(session, "Fidelity Brokerage")
            == Decimal("9500.00")
        )
