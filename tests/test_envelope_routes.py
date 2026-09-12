"""Integration tests for the /envelopes API endpoints."""

from decimal import Decimal
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from budget_app.models import Account
from budget_app.schemas import (
    AccountCreate,
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service, category_service, envelope_service, transaction_service


@pytest.fixture
def base_setup(session: Session):
    """Ensure base Cash account, Unassigned envelope, and starting categories exist."""
    cash = account_service.get_account(session, "Cash")
    if not cash:
        account_service.create_account(
            session,
            AccountCreate(
                name="Cash",
                account_type=AccountType.CASH,
                starting_balance=Decimal("2000.00"),
            ),
        )
    else:
        account_service.adjust_account_balance(
            session, account_name="Cash", target_balance=Decimal("2000.00")
        )

    category_service.create_category(session, name="Monthly Essentials")


class TestCreateEnvelopeRoute:
    def test_create_envelope_without_category(self, client: TestClient, base_setup):
        payload = {
            "name": "Groceries",
            "note": "Food and supplies",
            "is_active": True,
        }
        response = client.post("/envelopes/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Groceries"
        assert data["note"] == "Food and supplies"
        assert data["is_active"] is True
        assert Decimal(str(data["balance"])) == Decimal("0.00")
        assert data["category_id"] is None

    def test_create_envelope_with_category(self, client: TestClient, base_setup):
        payload = {
            "name": "Electricity",
            "category_name": "Monthly Essentials",
        }
        response = client.post("/envelopes/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["name"] == "Electricity"
        assert data["category_name"] == "Monthly Essentials"
        assert data["category_id"] is not None

    def test_create_envelope_empty_name_returns_400(self, client: TestClient, base_setup):
        payload = {"name": "   "}
        response = client.post("/envelopes/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Envelope name cannot be empty" in response.json()["detail"]

    def test_create_envelope_duplicate_name_returns_400(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Gasoline"})
        res = client.post("/envelopes/", json={"name": "Gasoline"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in res.json()["detail"]

    def test_create_envelope_nonexistent_category_returns_400(self, client: TestClient, base_setup):
        payload = {"name": "Internet", "category_name": "Ghost Category"}
        response = client.post("/envelopes/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not exist" in response.json()["detail"]


class TestGetEnvelopesRoute:
    def test_get_envelopes_returns_list(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Dining Out"})
        response = client.get("/envelopes/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        names = [e["name"] for e in data]
        assert "Dining Out" in names
        assert "Unassigned" in names

    def test_get_envelopes_filtering_by_active_status(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Gym Active", "is_active": True})
        client.post("/envelopes/", json={"name": "Old Gym Inactive", "is_active": False})

        res_active = client.get("/envelopes/?is_active=true")
        assert res_active.status_code == status.HTTP_200_OK
        active_names = [e["name"] for e in res_active.json()]
        assert "Gym Active" in active_names
        assert "Old Gym Inactive" not in active_names

        res_inactive = client.get("/envelopes/?is_active=false")
        assert res_inactive.status_code == status.HTTP_200_OK
        inactive_names = [e["name"] for e in res_inactive.json()]
        assert "Old Gym Inactive" in inactive_names
        assert "Gym Active" not in inactive_names


class TestGetEnvelopeByNameRoute:
    def test_get_envelope_by_name_success(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Rent & Mortgage", "note": "Monthly payment"})

        response = client.get("/envelopes/Rent & Mortgage")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Rent & Mortgage"
        assert data["note"] == "Monthly payment"
        assert "balance" in data

    def test_get_envelope_not_found(self, client: TestClient, base_setup):
        response = client.get("/envelopes/NonExistentEnvelope")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in response.json()["detail"]


class TestUpdateEnvelopeRoute:
    def test_update_envelope_note_and_category(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Streaming"})

        update_payload = {
            "note": "Netflix and Hulu",
            "category_name": "Monthly Essentials",
        }
        response = client.patch("/envelopes/Streaming", json=update_payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["note"] == "Netflix and Hulu"
        assert data["category_name"] == "Monthly Essentials"

    def test_update_envelope_name(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Old Env Name"})

        response = client.patch("/envelopes/Old Env Name", json={"name": "New Env Name"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "New Env Name"

        assert client.get("/envelopes/Old Env Name").status_code == status.HTTP_404_NOT_FOUND
        assert client.get("/envelopes/New Env Name").status_code == status.HTTP_200_OK

    def test_update_envelope_not_found(self, client: TestClient, base_setup):
        response = client.patch("/envelopes/GhostEnv", json={"name": "Whatever"})
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEnvelopeLifecycleRoutes:
    def test_deactivate_and_activate_envelope(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Seasonal Sports"})

        res_deact = client.post("/envelopes/Seasonal Sports/deactivate")
        assert res_deact.status_code == status.HTTP_200_OK
        assert res_deact.json()["is_active"] is False

        res_act = client.post("/envelopes/Seasonal Sports/activate")
        assert res_act.status_code == status.HTTP_200_OK
        assert res_act.json()["is_active"] is True

    def test_deactivate_system_envelope_rejected(self, client: TestClient, base_setup):
        response = client.post("/envelopes/Unassigned/deactivate")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "system envelope" in response.json()["detail"].lower()


class TestDeleteEnvelopeRoute:
    def test_delete_empty_envelope_success(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Temporary Envelope"})

        response = client.delete("/envelopes/Temporary Envelope")
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

        assert client.get("/envelopes/Temporary Envelope").status_code == status.HTTP_404_NOT_FOUND

    def test_delete_system_envelope_rejected(self, client: TestClient, base_setup):
        response = client.delete("/envelopes/Unassigned")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "system envelope" in response.json()["detail"].lower()


class TestEnvelopeTransfersAndFundingRoutes:
    def test_transfer_between_envelopes(self, client: TestClient, session: Session, base_setup):
        client.post("/envelopes/", json={"name": "Funded Env"})
        client.post("/envelopes/", json={"name": "Target Env"})

        # Put 100 in Funded Env
        envelope_service.assign_to_envelope(session, "Funded Env", Decimal("100.00"))

        transfer_payload = {
            "source_envelope": "Funded Env",
            "destination_envelope": "Target Env",
            "amount": "40.00",
            "note": "Rebalance",
        }
        response = client.post("/envelopes/transfer", json=transfer_payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert Decimal(str(data["new_balance_src"])) == Decimal("60.00")
        assert Decimal(str(data["new_balance_dest"])) == Decimal("40.00")

    def test_transfer_insufficient_funds_returns_400(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Source Broke"})
        client.post("/envelopes/", json={"name": "Dest Broke"})

        transfer_payload = {
            "source_envelope": "Source Broke",
            "destination_envelope": "Dest Broke",
            "amount": "50.00",
        }
        response = client.post("/envelopes/transfer", json=transfer_payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount too high" in response.json()["detail"].lower()

    def test_assign_envelope(self, client: TestClient, base_setup):
        client.post("/envelopes/", json={"name": "Emergency Fund"})

        payload = {
            "envelope_name": "Emergency Fund",
            "amount": "150.00",
            "note": "Rainy day",
        }
        response = client.post("/envelopes/assign", json=payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert Decimal(str(data["new_balance_dest"])) == Decimal("150.00")

    def test_add_income(self, client: TestClient, base_setup):
        payload = {
            "amount": "850.00",
            "source": "Side Gig",
            "note": "Freelance payout",
        }
        response = client.post("/envelopes/income", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["merchant"] == "Side Gig"
        assert Decimal(str(data["total"])) == Decimal("850.00")

    def test_add_income_negative_amount_returns_400(self, client: TestClient, base_setup):
        payload = {
            "amount": "-50.00",
            "source": "Bogus",
        }
        response = client.post("/envelopes/income", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
