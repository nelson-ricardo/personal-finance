"""Integration tests for the /accounts API endpoints."""

from decimal import Decimal
from fastapi import status
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Up and Running!"}


class TestCreateAccountRoute:
    def test_create_cash_account_success(self, client: TestClient):
        payload = {
            "name": "High Yield Savings",
            "account_type": "cash",
            "starting_balance": "1500.00",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "High Yield Savings"
        assert data["account_type"] == "cash"
        assert Decimal(str(data["current_balance"])) == Decimal("1500.00")
        assert data["is_active"] is True

    def test_create_credit_card_account_success(self, client: TestClient):
        payload = {
            "name": "Chase Sapphire",
            "account_type": "credit_card",
            "starting_balance": "350.00",
            "total_statement_balance": "500.00",
            "monthly_payment": "35.00",
            "due_date": "2026-10-01",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["name"] == "Chase Sapphire"
        assert data["account_type"] == "credit_card"
        assert data["envelope_id"] is not None
        assert Decimal(str(data["current_balance"])) == Decimal("350.00")
        assert Decimal(str(data["monthly_payment"])) == Decimal("35.00")
        assert data["due_date"] == "2026-10-01"

    def test_create_account_empty_name_returns_400(self, client: TestClient):
        payload = {
            "name": "   ",
            "account_type": "cash",
        }
        response = client.post("/accounts/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Account name cannot be empty" in response.json()["detail"]

    def test_create_account_duplicate_name_returns_400(self, client: TestClient):
        payload = {
            "name": "Checking Account",
            "account_type": "cash",
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


class TestGetAccountsRoute:
    def test_get_accounts_returns_list(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Travel Fund", "account_type": "cash", "starting_balance": "300.00"},
        )
        response = client.get("/accounts/")
        assert response.status_code == status.HTTP_200_OK

        accounts = response.json()
        assert isinstance(accounts, list)
        names = [acc["name"] for acc in accounts]
        assert "Travel Fund" in names

    def test_get_accounts_filtering_by_active_status(self, client: TestClient):
        # Create an account and archive it
        client.post(
            "/accounts/",
            json={"name": "Old Savings", "account_type": "cash", "starting_balance": "0.00"},
        )
        client.delete("/accounts/Old Savings")

        # Query only active
        res_active = client.get("/accounts/?is_active=true")
        assert res_active.status_code == status.HTTP_200_OK
        active_names = [a["name"] for a in res_active.json()]
        assert "Old Savings" not in active_names

        # Query only inactive/archived
        res_inactive = client.get("/accounts/?is_active=false")
        assert res_inactive.status_code == status.HTTP_200_OK
        inactive_names = [a["name"] for a in res_inactive.json()]
        assert "Old Savings" in inactive_names


class TestGetAccountByNameRoute:
    def test_get_account_by_name_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Vacation Stash", "account_type": "cash", "starting_balance": "800.00"},
        )

        response = client.get("/accounts/Vacation Stash")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Vacation Stash"
        assert Decimal(str(data["current_balance"])) == Decimal("800.00")

    def test_get_account_by_name_not_found(self, client: TestClient):
        response = client.get("/accounts/NonExistentAccount")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in response.json()["detail"]


class TestUpdateAccountRoute:
    def test_update_account_metadata_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Citi Double Cash", "account_type": "credit_card", "monthly_payment": "25.00"},
        )

        update_payload = {
            "monthly_payment": "75.00",
            "due_date": "2026-11-20",
        }
        response = client.patch("/accounts/Citi Double Cash", json=update_payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert Decimal(str(data["monthly_payment"])) == Decimal("75.00")
        assert data["due_date"] == "2026-11-20"

    def test_update_account_name_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "Initial Name", "account_type": "cash"},
        )

        response = client.patch("/accounts/Initial Name", json={"name": "Renamed Account"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Renamed Account"

        # Verify old name 404s and new name exists
        assert client.get("/accounts/Initial Name").status_code == status.HTTP_404_NOT_FOUND
        assert client.get("/accounts/Renamed Account").status_code == status.HTTP_200_OK

    def test_update_account_duplicate_name_returns_400(self, client: TestClient):
        client.post("/accounts/", json={"name": "Account Alpha", "account_type": "cash"})
        client.post("/accounts/", json={"name": "Account Beta", "account_type": "cash"})

        response = client.patch("/accounts/Account Alpha", json={"name": "Account Beta"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_update_nonexistent_account_returns_400(self, client: TestClient):
        response = client.patch("/accounts/GhostAccount", json={"name": "New Ghost"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeleteAccountRoute:
    def test_delete_account_success(self, client: TestClient):
        client.post(
            "/accounts/",
            json={"name": "To Be Deleted", "account_type": "cash", "starting_balance": "0.00"},
        )

        response = client.delete("/accounts/To Be Deleted")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "To Be Deleted"
        assert data["is_active"] is False

    def test_delete_nonexistent_account_returns_404(self, client: TestClient):
        response = client.delete("/accounts/NonExistentToDelete")
        assert response.status_code == status.HTTP_404_NOT_FOUND
