"""Tests for notification API routes and subscription management."""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_get_vapid_public_key(client: TestClient):
    response = client.get("/notifications/vapid-public-key")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "public_key" in data
    assert len(data["public_key"]) > 20


def test_subscribe_and_unsubscribe_device(client: TestClient, session: Session):
    sub_payload = {
        "endpoint": "https://push.example.com/sub/unique_device_token_123",
        "keys": {
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9t0",
            "auth": "tBHItJI5svbpez7KI4CCXg",
        },
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    }

    # 1. Subscribe device
    res = client.post("/notifications/subscribe", json=sub_payload)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["endpoint"] == sub_payload["endpoint"]
    assert "id" in data

    # 2. Verify subscription is listed
    list_res = client.get("/notifications/subscriptions")
    assert list_res.status_code == status.HTTP_200_OK
    subs = list_res.json()
    assert any(s["endpoint"] == sub_payload["endpoint"] for s in subs)

    # 3. Unsubscribe device
    unsub_res = client.delete(
        f"/notifications/unsubscribe?endpoint={sub_payload['endpoint']}"
    )
    assert unsub_res.status_code == status.HTTP_200_OK
    assert unsub_res.json()["removed"] is True

    # 4. Verify subscription removed
    list_res2 = client.get("/notifications/subscriptions")
    subs2 = list_res2.json()
    assert not any(s["endpoint"] == sub_payload["endpoint"] for s in subs2)


@patch("budget_app.services.notification_service.webpush")
def test_send_test_notification(mock_webpush, client: TestClient):
    mock_webpush.return_value = None

    # First subscribe a test client
    sub_payload = {
        "endpoint": "https://push.example.com/sub/test_device_456",
        "keys": {
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9t0",
            "auth": "tBHItJI5svbpez7KI4CCXg",
        },
        "user_agent": "TestBrowser/1.0",
    }
    client.post("/notifications/subscribe", json=sub_payload)

    # Trigger test notification
    test_res = client.post(
        "/notifications/test",
        json={"title": "Test Title", "body": "Test Body", "url": "/"},
    )
    assert test_res.status_code == status.HTTP_200_OK
    data = test_res.json()
    assert data["status"] == "completed"
    assert data["sent"] >= 1
    assert mock_webpush.called
