from decimal import Decimal
import pytest
from budget_app.schemas import AccountBase, AccountType
from budget_app.services import account_service


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
