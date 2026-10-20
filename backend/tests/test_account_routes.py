"""Integration tests for the /accounts API endpoints."""

from decimal import Decimal
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Up and Running!"}


class TestCreateAccountRoute:
    def test_create_second_cash_account_returns_400(self, client: TestClient):
        payload = {
            "name": "High Yield Savings",
            "account_type": "cash",
            "starting_balance": "1500.00",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only a single cash account is allowed" in response.json()["detail"]

    def test_create_credit_card_account_success(self, client: TestClient):
        payload = {
            "name": "Chase Sapphire",
            "account_type": "credit_card",
            "starting_balance": "350.00",
            "total_statement_balance": "500.00",
            "monthly_payment": "35.00",
            "due_date": 1,
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["name"] == "Chase Sapphire"
        assert data["account_type"] == "credit_card"
        assert data["envelope_id"] is not None
        assert Decimal(str(data["current_balance"])) == Decimal("350.00")
        assert Decimal(str(data["monthly_payment"])) == Decimal("35.00")
        assert data["due_date"] == 1

    def test_create_account_empty_name_returns_400(self, client: TestClient):
        payload = {
            "name": "   ",
            "account_type": "credit_card",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Account name cannot be empty" in response.json()["detail"]

    def test_create_account_duplicate_name_returns_400(self, client: TestClient):
        payload = {
            "name": "Duplicate Card",
            "account_type": "credit_card",
            "starting_balance": "100.00",
        }
        # First creation succeeds
        res1 = client.post("/accounts/", json=payload)
        assert res1.status_code == status.HTTP_201_CREATED

        # Duplicate creation fails
        res2 = client.post("/accounts/", json=payload)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in res2.json()["detail"]

    def test_create_cash_account_negative_balance_returns_400(self, client: TestClient):
        payload = {
            "name": "Overdrawn Account",
            "account_type": "cash",
            "starting_balance": "-50.00",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "negative" in response.json()["detail"].lower()

    def test_create_account_invalid_type_returns_422(self, client: TestClient):
        payload = {
            "name": "Crypto Wallet",
            "account_type": "crypto",  # invalid enum value
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize("invalid_due_date", [0, 32, -5, "2026-10-01"])
    def test_create_account_invalid_due_date_returns_422(self, client: TestClient, invalid_due_date):
        payload = {
            "name": "Invalid Due Date Card",
            "account_type": "credit_card",
            "due_date": invalid_due_date,
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestGetAccountsRoute:
    def test_get_accounts_returns_list(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Travel Card", "account_type": "credit_card", "starting_balance": "300.00"},
        )
        response = client.get("/accounts/")
        assert response.status_code == status.HTTP_200_OK

        accounts = response.json()
        assert isinstance(accounts, list)
        names = [acc["name"] for acc in accounts]
        assert "Cash" in names
        assert "Travel Card" in names

    def test_get_accounts_filtering_by_active_status(self, client: TestClient):
        # Create an account and archive it
        client.post(
            "/accounts/",
            json={"name": "Old Card", "account_type": "credit_card", "starting_balance": "0.00"},
        )
        client.delete("/accounts/Old Card")

        # Query only active
        res_active = client.get("/accounts/?is_active=true")
        assert res_active.status_code == status.HTTP_200_OK
        active_names = [a["name"] for a in res_active.json()]
        assert "Old Card" not in active_names

        # Query only inactive/archived
        res_inactive = client.get("/accounts/?is_active=false")
        assert res_inactive.status_code == status.HTTP_200_OK
        inactive_names = [a["name"] for a in res_inactive.json()]
        assert "Old Card" in inactive_names

        # Query all accounts (default in /accounts/) returns both active and inactive
        res_all = client.get("/accounts/")
        assert res_all.status_code == status.HTTP_200_OK
        all_names = [a["name"] for a in res_all.json()]
        assert "Old Card" in all_names
        assert "Cash" in all_names


class TestGetAccountByNameRoute:
    def test_get_account_by_name_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Vacation Card", "account_type": "credit_card", "starting_balance": "800.00"},
        )

        response = client.get("/accounts/Vacation Card")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Vacation Card"
        assert Decimal(str(data["current_balance"])) == Decimal("800.00")

    def test_get_account_by_name_not_found(self, client: TestClient):
        response = client.get("/accounts/NonExistentAccount")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in response.json()["detail"]


class TestUpdateAccountRoute:
    def test_update_account_metadata_success(self, client: TestClient):
        res = client.post(
            "/accounts/",
            json={"name": "Citi Double Cash", "account_type": "credit_card", "monthly_payment": "25.00"},
        )
        account_id = res.json()["id"]

        update_payload = {
            "monthly_payment": "75.00",
            "due_date": 20,
        }
        response = client.patch(f"/accounts/{account_id}", json=update_payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert Decimal(str(data["monthly_payment"])) == Decimal("75.00")
        assert data["due_date"] == 20

    def test_update_account_name_success(self, client: TestClient):
        res = client.post(
            "/accounts/",
            json={"name": "Initial Name", "account_type": "credit_card"},
        )
        account_id = res.json()["id"]

        response = client.patch(f"/accounts/{account_id}", json={"name": "Renamed Account"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Renamed Account"
        assert response.json()["id"] == account_id

        # Verify old name 404s and new name exists
        assert client.get("/accounts/Initial Name").status_code == status.HTTP_404_NOT_FOUND
        assert client.get("/accounts/Renamed Account").status_code == status.HTTP_200_OK

    def test_update_account_duplicate_name_returns_400(self, client: TestClient):
        res_a = client.post("/accounts/", json={"name": "Account Alpha", "account_type": "credit_card"})
        client.post("/accounts/", json={"name": "Account Beta", "account_type": "credit_card"})
        account_a_id = res_a.json()["id"]

        response = client.patch(f"/accounts/{account_a_id}", json={"name": "Account Beta"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_update_nonexistent_account_returns_404(self, client: TestClient):
        response = client.patch("/accounts/99999", json={"name": "New Ghost"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_account_invalid_id_returns_422(self, client: TestClient):
        response = client.patch("/accounts/notanint", json={"name": "New Ghost"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestDeleteAccountRoute:
    def test_delete_account_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "To Be Deleted", "account_type": "credit_card", "starting_balance": "0.00"},
        )

        response = client.delete("/accounts/To Be Deleted")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "To Be Deleted"
        assert data["is_active"] is False

    def test_delete_nonexistent_account_returns_404(self, client: TestClient):
        response = client.delete("/accounts/NonExistentToDelete")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestActivateAccountRoute:
    def test_activate_archived_account_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Reactivatable", "account_type": "credit_card", "starting_balance": "0.00"},
        )
        # Archive it first
        res_del = client.delete("/accounts/Reactivatable")
        assert res_del.status_code == status.HTTP_200_OK
        assert res_del.json()["is_active"] is False

        # Reactivate it
        res_act = client.post("/accounts/Reactivatable/activate")
        assert res_act.status_code == status.HTTP_200_OK
        data = res_act.json()
        assert data["name"] == "Reactivatable"
        assert data["is_active"] is True

    def test_activate_nonexistent_account_returns_404(self, client: TestClient):
        response = client.post("/accounts/NonExistentToActivate/activate")
        assert response.status_code == status.HTTP_404_NOT_FOUND
