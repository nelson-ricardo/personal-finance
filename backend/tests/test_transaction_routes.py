"""Integration tests for the /transactions API endpoints."""

from decimal import Decimal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from budget_app.repositories import envelope_repo
from budget_app.schemas import (
    AccountCreate,
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service, transaction_service


@pytest.fixture
def test_setup(session: Session):
    """Sets up standard accounts and envelopes for transaction testing."""
    # Create or fetch Cash account with funds
    cash = account_service.get_account(session, "Cash")
    if not cash:
        account_service.create_account(
            session,
            AccountCreate(name="Cash", account_type=AccountType.CASH, starting_balance=Decimal("2000.00")),
        )
    else:
        # Give Cash account starting balance if zero
        account_service.adjust_account_balance(
            session, account_name="Cash", target_balance=Decimal("2000.00")
        )

    # Create Credit Card account
    cc = account_service.get_account(session, "Visa Card")
    if not cc:
        account_service.create_account(
            session,
            AccountCreate(
                name="Visa Card",
                account_type=AccountType.CREDIT_CARD,
                starting_balance=Decimal("200.00"),
                total_statement_balance=Decimal("300.00"),
                monthly_payment=Decimal("25.00"),
            ),
        )

    # Create Envelopes
    for env_name in ["Groceries", "Utilities", "Dining"]:
        envelope_repo.get_or_create_envelope(session, EnvelopeBase(name=env_name))

    # Fund Groceries envelope with $500
    transaction_service.add_reg_transaction(
        session,
        TransactionRequest(
            merchant="Paycheck",
            payment_method_name="Cash",
            transaction_type=TransactionType.INCOME,
            splits=[EnvelopeSplitRequest(amount=Decimal("500.00"), envelope_name="Groceries")],
        ),
    )


class TestAddRegularTransactionRoute:
    def test_create_regular_expense_cash(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Whole Foods",
            "payment_method_name": "Cash",
            "transaction_type": "EXPENSE",
            "note": "Weekly shopping",
            "splits": [
                {"envelope_name": "Groceries", "amount": "-75.50"}
            ],
        }
        response = client.post("/transactions/regular", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["merchant"] == "Whole Foods"
        assert data["payment_method_name"] == "Cash"
        assert Decimal(str(data["total"])) == Decimal("75.50")
        assert data["note"] == "Weekly shopping"

    def test_create_regular_expense_credit_card(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Electric Company",
            "payment_method_name": "Visa Card",
            "transaction_type": "EXPENSE",
            "splits": [
                {"envelope_name": "Utilities", "amount": "-120.00"}
            ],
        }
        response = client.post("/transactions/regular", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["merchant"] == "Electric Company"
        assert data["payment_method_name"] == "Visa Card"
        assert Decimal(str(data["total"])) == Decimal("120.00")

    def test_create_regular_transaction_nonexistent_account(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Store",
            "payment_method_name": "NonExistentBank",
            "transaction_type": "EXPENSE",
            "splits": [{"envelope_name": "Groceries", "amount": "-20.00"}],
        }
        response = client.post("/transactions/regular", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not exist" in response.json()["detail"].lower()

    def test_create_regular_transaction_nonexistent_envelope(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Store",
            "payment_method_name": "Cash",
            "transaction_type": "EXPENSE",
            "splits": [{"envelope_name": "NoSuchEnvelope", "amount": "-20.00"}],
        }
        response = client.post("/transactions/regular", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not exist" in response.json()["detail"].lower()


class TestAddFinancedTransactionRoute:
    def test_create_financed_transaction_credit_card(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Apple Store",
            "payment_method_name": "Visa Card",
            "amount": "1200.00",
            "term": 12,
            "description": "MacBook Pro installment",
        }
        response = client.post("/transactions/financed", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["merchant"] == "Apple Store"
        assert data["payment_method_name"] == "Visa Card"
        assert Decimal(str(data["total"])) == Decimal("1200.00")

    def test_create_financed_transaction_cash_fails(self, client: TestClient, test_setup):
        payload = {
            "merchant": "Apple Store",
            "payment_method_name": "Cash",
            "amount": "1200.00",
            "term": 12,
        }
        response = client.post("/transactions/financed", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetTransactionsRoute:
    def test_get_transactions_list(self, client: TestClient, test_setup):
        response = client.get("/transactions/")
        assert response.status_code == status.HTTP_200_OK

        txs = response.json()
        assert isinstance(txs, list)
        assert len(txs) > 0

    def test_get_transactions_filter_by_account(self, client: TestClient, test_setup):
        response = client.get("/transactions/?account=Cash")
        assert response.status_code == status.HTTP_200_OK

        for tx in response.json():
            assert tx["payment_method_name"] == "Cash"

    def test_get_transactions_filter_by_envelope(self, client: TestClient, test_setup):
        response = client.get("/transactions/?envelope=Groceries")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_transactions_filter_by_type(self, client: TestClient, test_setup):
        response = client.get("/transactions/?transaction_type=INCOME")
        assert response.status_code == status.HTTP_200_OK
        for tx in response.json():
            assert tx["transaction_type"] == "INCOME"


class TestGetTransactionByIdRoute:
    def test_get_transaction_by_id_success(self, client: TestClient, test_setup):
        # Create a transaction to query
        create_res = client.post(
            "/transactions/regular",
            json={
                "merchant": "Target",
                "payment_method_name": "Cash",
                "transaction_type": "EXPENSE",
                "splits": [{"envelope_name": "Dining", "amount": "-45.00"}],
            },
        )
        tx_id = create_res.json()["id"]

        # Fetch it by ID
        detail_res = client.get(f"/transactions/{tx_id}")
        assert detail_res.status_code == status.HTTP_200_OK

        data = detail_res.json()
        assert data["id"] == tx_id
        assert data["merchant"] == "Target"
        assert Decimal(str(data["total"])) == Decimal("45.00")
        assert len(data["splits"]) == 1
        assert data["splits"][0]["envelope_name"] == "Dining"

    def test_get_transaction_by_id_not_found(self, client: TestClient, test_setup):
        response = client.get("/transactions/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in response.json()["detail"].lower()


class TestUpdateTransactionRoute:
    def test_update_regular_transaction_metadata(self, client: TestClient, test_setup):
        create_res = client.post(
            "/transactions/regular",
            json={
                "merchant": "Coffee Shop",
                "payment_method_name": "Cash",
                "transaction_type": "EXPENSE",
                "note": "Old Note",
                "splits": [{"envelope_name": "Dining", "amount": "-5.50"}],
            },
        )
        tx_id = create_res.json()["id"]

        update_payload = {
            "merchant": "Artisan Cafe",
            "note": "Updated Note",
        }
        update_res = client.patch(f"/transactions/regular/{tx_id}", json=update_payload)
        assert update_res.status_code == status.HTTP_200_OK

        data = update_res.json()
        assert data["merchant"] == "Artisan Cafe"
        assert data["note"] == "Updated Note"

    def test_update_financed_transaction(self, client: TestClient, test_setup):
        fin_res = client.post(
            "/transactions/financed",
            json={
                "merchant": "Best Buy",
                "payment_method_name": "Visa Card",
                "amount": "600.00",
                "term": 6,
            },
        )
        tx_id = fin_res.json()["id"]

        update_res = client.patch(
            f"/transactions/financed/{tx_id}",
            json={"merchant": "Best Buy Online", "term": 12},
        )
        assert update_res.status_code == status.HTTP_200_OK
        assert update_res.json()["merchant"] == "Best Buy Online"

    def test_update_nonexistent_transaction_returns_400(self, client: TestClient, test_setup):
        response = client.patch(
            "/transactions/regular/999999",
            json={"merchant": "Ghost"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeleteTransactionRoute:
    def test_delete_transaction_creates_reversal(self, client: TestClient, test_setup):
        create_res = client.post(
            "/transactions/regular",
            json={
                "merchant": "To Be Reversed",
                "payment_method_name": "Cash",
                "transaction_type": "EXPENSE",
                "splits": [{"envelope_name": "Groceries", "amount": "-25.00"}],
            },
        )
        tx_id = create_res.json()["id"]

        del_res = client.delete(f"/transactions/{tx_id}")
        assert del_res.status_code == status.HTTP_200_OK

        data = del_res.json()
        assert data["transaction_type"] == "REVERSAL"

    def test_delete_already_reversed_transaction_returns_400(self, client: TestClient, test_setup):
        create_res = client.post(
            "/transactions/regular",
            json={
                "merchant": "Reverse Twice",
                "payment_method_name": "Cash",
                "transaction_type": "EXPENSE",
                "splits": [{"envelope_name": "Groceries", "amount": "-25.00"}],
            },
        )
        tx_id = create_res.json()["id"]

        # First reversal succeeds
        res1 = client.delete(f"/transactions/{tx_id}")
        assert res1.status_code == status.HTTP_200_OK

        # Second reversal attempt fails
        res2 = client.delete(f"/transactions/{tx_id}")
        assert res2.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_nonexistent_transaction_returns_400(self, client: TestClient, test_setup):
        response = client.delete("/transactions/999999")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPaymentsAndAdjustmentsRoutes:
    def test_make_payment_success(self, client: TestClient, test_setup):
        # Fund the credit card payment envelope so there are funds to pay
        client.post(
            "/transactions/regular",
            json={
                "merchant": "Deposit to CC Payment",
                "payment_method_name": "Cash",
                "transaction_type": "INCOME",
                "splits": [{"envelope_name": "Credit Card Payment", "amount": "100.00"}],
            },
        )

        pay_payload = {
            "account": "Visa Card",
            "amount": "50.00",
        }
        res = client.post("/transactions/payments", json=pay_payload)
        assert res.status_code == status.HTTP_201_CREATED

        transactions = res.json()
        assert isinstance(transactions, list)
        assert len(transactions) == 1
        assert transactions[0]["merchant"] == "Payment for Visa Card"

    def test_make_payment_nonexistent_account(self, client: TestClient, test_setup):
        res = client.post(
            "/transactions/payments",
            json={"account": "FakeBank", "amount": "50.00"},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_make_payment_negative_amount(self, client: TestClient, test_setup):
        res = client.post(
            "/transactions/payments",
            json={"account": "Visa Card", "amount": "-20.00"},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_adjust_account_balance_when_needed(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Cash",
            "target_balance": "3500.00",
            "note": "Found extra cash in safe",
        }
        res = client.post("/transactions/account-adjustment", json=payload)
        assert res.status_code == status.HTTP_201_CREATED

        data = res.json()
        assert "id" in data
        assert data["payment_method_name"] == "Cash"

    def test_adjust_account_balance_already_matches(self, client: TestClient, test_setup):
        # Fetch current balance of Cash account
        acct_res = client.get("/accounts/Cash")
        current_bal = str(acct_res.json()["current_balance"])

        payload = {
            "account_name": "Cash",
            "target_balance": current_bal,
        }
        res = client.post("/transactions/account-adjustment", json=payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json() == {"message": "Account balance already matches"}


class TestInterestTransactionsRoute:
    def test_add_interest_charge_on_credit_card(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Visa Card",
            "amount": "14.50",
            "note": "Monthly APR charge",
        }
        response = client.post("/transactions/interest-charge", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["transaction_type"] == "INTEREST_CHARGE"
        assert data["payment_method_name"] == "Visa Card"
        assert Decimal(str(data["total"])) == Decimal("14.50")
        assert data["note"] == "Monthly APR charge"

    def test_add_interest_charge_on_cash_account_rejected(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Cash",
            "amount": "10.00",
        }
        response = client.post("/transactions/interest-charge", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "debt accounts" in response.json()["detail"]

    def test_add_interest_charge_negative_amount_rejected(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Visa Card",
            "amount": "-5.00",
        }
        response = client.post("/transactions/interest-charge", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_interest_earned_on_cash_account(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Cash",
            "amount": "22.75",
            "note": "HYSA dividend",
        }
        response = client.post("/transactions/interest-earned", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["transaction_type"] == "INTEREST_EARNED"
        assert data["payment_method_name"] == "Cash"
        assert Decimal(str(data["total"])) == Decimal("22.75")
        assert data["note"] == "HYSA dividend"

    def test_add_interest_earned_on_credit_card_rejected(self, client: TestClient, test_setup):
        payload = {
            "account_name": "Visa Card",
            "amount": "15.00",
        }
        response = client.post("/transactions/interest-earned", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cash/Savings" in response.json()["detail"]
