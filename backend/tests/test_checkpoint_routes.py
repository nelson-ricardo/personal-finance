"""Integration tests for the /dev/checkpoints API endpoints."""

from decimal import Decimal
from pathlib import Path
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlmodel import Session

from budget_app.api.routes import accounts, categories, dev as dev_routes
from budget_app.db import get_session
from budget_app.services import checkpoint_service


@pytest.fixture(autouse=True)
def setup_test_checkpoints_dir(tmp_path, monkeypatch):
    """Overrides the checkpoints directory to a temporary path for isolated testing."""
    test_dir = tmp_path / "test_checkpoints"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CHECKPOINTS_DIR", str(test_dir))
    return test_dir


@pytest.fixture
def dev_client(session: Session) -> TestClient:
    """TestClient instance with dev router mounted."""
    test_app = FastAPI()
    test_app.include_router(accounts.router)
    test_app.include_router(categories.router)
    test_app.include_router(dev_routes.router)
    test_app.dependency_overrides[get_session] = lambda: session
    with TestClient(test_app) as tc:
        yield tc
    test_app.dependency_overrides.clear()


class TestCheckpointRoutes:
    def test_create_list_restore_and_delete_checkpoint(self, dev_client: TestClient):
        # 1. Create an initial account and category
        cat_res = dev_client.post("/categories/", json={"name": "Groceries Group"})
        assert cat_res.status_code == status.HTTP_201_CREATED

        acc_res = dev_client.post(
            "/accounts/",
            json={"name": "Chase Freedom", "account_type": "credit_card", "starting_balance": "500.00"},
        )
        assert acc_res.status_code == status.HTTP_201_CREATED

        # 2. Take a checkpoint snapshot
        snap_res = dev_client.post(
            "/dev/checkpoints",
            json={"name": "Baseline Checkpoint"},
        )
        assert snap_res.status_code == status.HTTP_201_CREATED
        snap_data = snap_res.json()
        checkpoint_id = snap_data["id"]
        assert snap_data["name"] == "Baseline Checkpoint"
        assert snap_data["stats"]["accounts_count"] >= 1
        assert snap_data["stats"]["categories_count"] >= 1

        # 3. List checkpoints
        list_res = dev_client.get("/dev/checkpoints")
        assert list_res.status_code == status.HTTP_200_OK
        checkpoints = list_res.json()
        assert any(c["id"] == checkpoint_id for c in checkpoints)

        # 4. Modify state by creating another account
        acc2_res = dev_client.post(
            "/accounts/",
            json={"name": "Temp Auto Loan", "account_type": "loan", "starting_balance": "1000.00"},
        )
        assert acc2_res.status_code == status.HTTP_201_CREATED

        # Verify new card exists
        verify_res = dev_client.get("/accounts/")
        names = [a["name"] for a in verify_res.json()]
        assert "Temp Auto Loan" in names

        # 5. Restore database from baseline checkpoint
        restore_res = dev_client.post(f"/dev/checkpoints/{checkpoint_id}/restore")
        assert restore_res.status_code == status.HTTP_200_OK
        restore_data = restore_res.json()
        assert restore_data["status"] == "restored"

        # Verify state was rolled back (Temp Auto Loan should no longer exist)
        after_res = dev_client.get("/accounts/")
        names_after = [a["name"] for a in after_res.json()]
        assert "Temp Auto Loan" not in names_after
        assert "Chase Freedom" in names_after

        # 6. Delete checkpoint
        del_res = dev_client.delete(f"/dev/checkpoints/{checkpoint_id}")
        assert del_res.status_code == status.HTTP_200_OK

        # Verify it's gone from list
        list_after = dev_client.get("/dev/checkpoints").json()
        assert not any(c["id"] == checkpoint_id for c in list_after)
