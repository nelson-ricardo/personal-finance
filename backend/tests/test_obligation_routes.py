"""Tests for Obligations API routes, account synchronization, and reminder scheduling."""

from decimal import Decimal
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from budget_app.models.account import Account
from budget_app.schemas.account import AccountType


def test_create_and_get_obligation(client: TestClient):
    payload = {
        "name": "Apartment Rent",
        "due_day": 1,
        "amount": 1800.00,
        "note": "Pay online via resident portal",
    }
    create_res = client.post("/obligations/", json=payload)
    assert create_res.status_code == status.HTTP_201_CREATED
    data = create_res.json()
    assert data["name"] == "Apartment Rent"
    assert data["due_day"] == 1
    assert Decimal(str(data["amount"])) == Decimal("1800.00")
    assert data["note"] == "Pay online via resident portal"
    assert "days_until_due" in data
    assert "next_due_date" in data

    obl_id = data["id"]

    # Verify in list
    list_res = client.get("/obligations/")
    assert list_res.status_code == status.HTTP_200_OK
    obls = list_res.json()
    assert any(o["id"] == obl_id for o in obls)


def test_sync_obligations_from_accounts(client: TestClient, session: Session):
    # 1. Create a credit card account with due date and monthly payment
    card = Account(
        name="Apple Card Test",
        account_type=AccountType.CREDIT_CARD,
        monthly_payment=Decimal("75.00"),
        due_date=20,
        is_active=True,
    )
    session.add(card)
    session.commit()
    session.refresh(card)

    # 2. Trigger sync
    sync_res = client.post("/obligations/sync-accounts")
    assert sync_res.status_code == status.HTTP_200_OK
    sync_data = sync_res.json()
    assert sync_data["accounts_scanned"] >= 1

    # 3. Verify obligation was created with default note
    list_res = client.get("/obligations/")
    assert list_res.status_code == status.HTTP_200_OK
    obls = list_res.json()
    matched = [o for o in obls if o["account_id"] == card.id]
    assert len(matched) == 1
    assert matched[0]["name"] == "Apple Card Test"
    assert matched[0]["due_day"] == 20
    assert Decimal(str(matched[0]["amount"])) == Decimal("75.00")
    assert matched[0]["note"] == "Monthly payment for Apple Card Test"


def test_mark_obligation_paid_and_unpaid(client: TestClient):
    payload = {
        "name": "Electric Utility",
        "due_day": 10,
        "amount": 95.50,
        "note": "Power company",
    }
    create_res = client.post("/obligations/", json=payload)
    assert create_res.status_code == status.HTTP_201_CREATED
    obl_id = create_res.json()["id"]

    # Mark as paid
    pay_res = client.post(f"/obligations/{obl_id}/pay", json={"paid": True})
    assert pay_res.status_code == status.HTTP_200_OK
    data = pay_res.json()
    assert data["is_paid_this_month"] is True
    assert data["last_paid_date"] is not None

    # Mark as unpaid
    unpay_res = client.post(f"/obligations/{obl_id}/pay", json={"paid": False})
    assert unpay_res.status_code == status.HTTP_200_OK
    data_unpay = unpay_res.json()
    assert data_unpay["is_paid_this_month"] is False
    assert data_unpay["last_paid_date"] is None


def test_notification_settings_api(client: TestClient):
    # Get settings
    get_res = client.get("/notifications/settings")
    assert get_res.status_code == status.HTTP_200_OK
    data = get_res.json()
    assert "reminder_time" in data
    assert "reminder_days_ahead" in data

    # Update settings
    put_res = client.put(
        "/notifications/settings",
        json={"reminder_time": "08:30", "reminder_days_ahead": 5, "is_enabled": True},
    )
    assert put_res.status_code == status.HTTP_200_OK
    updated = put_res.json()
    assert updated["reminder_time"] == "08:30"
    assert updated["reminder_days_ahead"] == 5
    assert updated["is_enabled"] is True


@patch("budget_app.services.notification_service.webpush")
def test_run_due_reminders(mock_webpush, client: TestClient):
    mock_webpush.return_value = None

    # Create an obligation due today or within 3 days
    from datetime import date
    today = date.today()

    client.post(
        "/obligations/",
        json={
            "name": "Upcoming Bill",
            "due_day": today.day,
            "amount": 50.00,
            "note": "Due soon",
        },
    )

    # Subscribe dummy device
    client.post(
        "/notifications/subscribe",
        json={
            "endpoint": "https://push.example.com/sub/due_reminder_device",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9t0",
                "auth": "tBHItJI5svbpez7KI4CCXg",
            },
        },
    )

    # Run reminders
    rem_res = client.post("/notifications/run-reminders?force=true")
    assert rem_res.status_code == status.HTTP_200_OK
    res_data = rem_res.json()
    assert res_data["status"] == "dispatched"
    assert res_data["due_count"] >= 1
