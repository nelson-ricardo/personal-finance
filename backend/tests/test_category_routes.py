"""Integration tests for the /categories API endpoints."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from budget_app.schemas import EnvelopeBase
from budget_app.services import envelope_service


class TestCreateCategoryRoute:
    def test_create_category_success(self, client: TestClient):
        payload = {
            "name": "Housing",
            "order_index": 1,
            "is_active": True,
        }
        response = client.post("/categories/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Housing"
        assert data["order_index"] == 1
        assert data["is_active"] is True

    def test_create_category_whitespace_trimmed(self, client: TestClient):
        payload = {
            "name": "   Transportation   ",
            "order_index": 2,
        }
        response = client.post("/categories/", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Transportation"

    def test_create_category_empty_name_returns_400(self, client: TestClient):
        payload = {"name": "   ", "order_index": 0}
        response = client.post("/categories/", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Category name cannot be empty" in response.json()["detail"]

    def test_create_category_duplicate_name_returns_400(self, client: TestClient):
        payload = {"name": "Food & Dining", "order_index": 0}
        res1 = client.post("/categories/", json=payload)
        assert res1.status_code == status.HTTP_201_CREATED

        res2 = client.post("/categories/", json=payload)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in res2.json()["detail"]


class TestGetCategoriesRoute:
    def test_get_categories_returns_list(self, client: TestClient):
        client.post("/categories/", json={"name": "Health & Fitness", "order_index": 1})
        client.post("/categories/", json={"name": "Entertainment", "order_index": 2})

        response = client.get("/categories/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        names = [c["name"] for c in data]
        assert "Health & Fitness" in names
        assert "Entertainment" in names

    def test_get_categories_filtering_by_active_status(self, client: TestClient):
        client.post("/categories/", json={"name": "Active Category"})
        client.post("/categories/", json={"name": "Inactive Category"})
        client.patch("/categories/Inactive Category", json={"is_active": False})

        res_active = client.get("/categories/?is_active=true")
        assert res_active.status_code == status.HTTP_200_OK
        active_names = [c["name"] for c in res_active.json()]
        assert "Active Category" in active_names
        assert "Inactive Category" not in active_names

        res_inactive = client.get("/categories/?is_active=false")
        assert res_inactive.status_code == status.HTTP_200_OK
        inactive_names = [c["name"] for c in res_inactive.json()]
        assert "Inactive Category" in inactive_names
        assert "Active Category" not in inactive_names


class TestGetCategoriesWithEnvelopesRoute:
    def test_get_categories_with_envelopes(self, client: TestClient, session: Session):
        client.post("/categories/", json={"name": "Living Expenses", "order_index": 1})
        envelope_service.create_envelope(
            session=session,
            envelope_info=EnvelopeBase(name="Rent"),
            category_name="Living Expenses",
        )

        response = client.get("/categories/with-envelopes")
        assert response.status_code == status.HTTP_200_OK

        groups = response.json()
        assert isinstance(groups, list)
        living_group = next((g for g in groups if g["name"] == "Living Expenses"), None)
        assert living_group is not None
        assert "total_balance" in living_group
        env_names = [e["name"] for e in living_group["envelopes"]]
        assert "Rent" in env_names


class TestGetCategoryByNameRoute:
    def test_get_category_by_name_success(self, client: TestClient):
        client.post("/categories/", json={"name": "Utilities", "order_index": 3})

        response = client.get("/categories/Utilities")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Utilities"
        assert data["order_index"] == 3

    def test_get_category_by_name_not_found(self, client: TestClient):
        response = client.get("/categories/NonExistentCategory")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in response.json()["detail"]


class TestUpdateCategoryRoute:
    def test_update_category_name_and_order(self, client: TestClient):
        client.post("/categories/", json={"name": "Old Category", "order_index": 1})

        update_payload = {"name": "New Category", "order_index": 5}
        response = client.patch("/categories/Old Category", json=update_payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Category"
        assert data["order_index"] == 5

        # Old name should 404, new name should exist
        assert client.get("/categories/Old Category").status_code == status.HTTP_404_NOT_FOUND
        assert client.get("/categories/New Category").status_code == status.HTTP_200_OK

    def test_update_category_duplicate_name_returns_400(self, client: TestClient):
        client.post("/categories/", json={"name": "Cat Alpha"})
        client.post("/categories/", json={"name": "Cat Beta"})

        response = client.patch("/categories/Cat Alpha", json={"name": "Cat Beta"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_update_category_not_found_returns_404(self, client: TestClient):
        response = client.patch("/categories/GhostCategory", json={"name": "RealName"})
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteCategoryRoute:
    def test_delete_empty_category_success(self, client: TestClient):
        client.post("/categories/", json={"name": "Empty Group"})

        response = client.delete("/categories/Empty Group")
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

        assert client.get("/categories/Empty Group").status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_with_envelopes_returns_400(self, client: TestClient, session: Session):
        client.post("/categories/", json={"name": "Populated Group"})
        envelope_service.create_envelope(
            session=session,
            envelope_info=EnvelopeBase(name="Child Envelope"),
            category_name="Populated Group",
        )

        response = client.delete("/categories/Populated Group")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "contains 1 envelope(s)" in response.json()["detail"]

    def test_delete_nonexistent_category_returns_404(self, client: TestClient):
        response = client.delete("/categories/NonExistentToDelete")
        assert response.status_code == status.HTTP_404_NOT_FOUND
