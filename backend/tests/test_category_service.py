"""Unit tests for category_service."""

from decimal import Decimal

import pytest

from budget_app.schemas import (
    EnvelopeBase,
    EnvelopeCategoryUpdate,
)
from budget_app.services import (
    category_service,
    envelope_service,
)


class TestCreateCategory:
    def test_create_category_success(self, session):
        category = category_service.create_category(
            session, name="Fixed Monthly Expenses", order_index=1
        )
        assert category.id is not None
        assert category.name == "Fixed Monthly Expenses"
        assert category.order_index == 1
        assert category.is_active is True

    def test_create_category_whitespace_trimmed(self, session):
        category = category_service.create_category(
            session, name="  Savings  ", order_index=3
        )
        assert category.name == "Savings"

    def test_create_category_empty_name_raises(self, session):
        with pytest.raises(ValueError, match="Category name cannot be empty"):
            category_service.create_category(session, name="   ")

    def test_create_category_duplicate_name_raises(self, session):
        category_service.create_category(session, name="Wants")
        with pytest.raises(ValueError, match="Category already exists"):
            category_service.create_category(session, name="Wants")


class TestGetCategory:
    def test_get_category_by_name_success(self, session):
        created = category_service.create_category(session, name="Subscriptions")
        found = category_service.get_category_by_name(session, "Subscriptions")
        assert found.id == created.id
        assert found.name == "Subscriptions"

    def test_get_category_by_name_nonexistent_raises(self, session):
        with pytest.raises(ValueError, match="Category 'NonExistent' does not exist"):
            category_service.get_category_by_name(session, "NonExistent")

    def test_get_category_by_name_empty_raises(self, session):
        with pytest.raises(ValueError, match="Category name cannot be empty"):
            category_service.get_category_by_name(session, "   ")

    def test_get_category_by_id_success(self, session):
        created = category_service.create_category(session, name="Utilities")
        assert created.id is not None
        found = category_service.get_category_by_id(session, created.id)
        assert found.id == created.id
        assert found.name == "Utilities"

    def test_get_category_by_id_nonexistent_raises(self, session):
        with pytest.raises(ValueError, match="Category ID 99999 does not exist"):
            category_service.get_category_by_id(session, 99999)

    def test_get_categories_ordering(self, session):
        category_service.create_category(session, name="Zebra", order_index=10)
        category_service.create_category(session, name="Apple", order_index=1)
        category_service.create_category(session, name="Banana", order_index=1)

        categories = category_service.get_categories(session)
        # Order should be by order_index, then name
        names = [c.name for c in categories]
        assert names.index("Apple") < names.index("Banana")
        assert names.index("Banana") < names.index("Zebra")


class TestUpdateCategory:
    def test_update_category_name(self, session):
        category_service.create_category(session, name="Old Name", order_index=1)
        updated = category_service.update_category(
            session, "Old Name", EnvelopeCategoryUpdate(name="New Name")
        )
        assert updated.name == "New Name"
        assert category_service.get_category_by_name(session, "New Name") is not None

    def test_update_category_duplicate_name_raises(self, session):
        category_service.create_category(session, name="Cat A")
        category_service.create_category(session, name="Cat B")
        with pytest.raises(ValueError, match="Category 'Cat B' already exists"):
            category_service.update_category(
                session, "Cat A", EnvelopeCategoryUpdate(name="Cat B")
            )

    def test_update_category_order_and_active(self, session):
        category_service.create_category(session, name="Cat Order", order_index=1)
        updated = category_service.update_category(
            session,
            "Cat Order",
            EnvelopeCategoryUpdate(order_index=5, is_active=False),
        )
        assert updated.order_index == 5
        assert updated.is_active is False


class TestDeleteCategory:
    def test_delete_empty_category_success(self, session):
        category_service.create_category(session, name="Empty Category")
        category_service.delete_category(session, "Empty Category")

        with pytest.raises(ValueError, match="does not exist"):
            category_service.get_category_by_name(session, "Empty Category")

    def test_delete_category_with_envelopes_raises(self, session):
        category_service.create_category(session, name="Bills")
        envelope_service.create_envelope(
            session,
            EnvelopeBase(name="Electric"),
            category_name="Bills",
        )

        with pytest.raises(
            ValueError, match="Cannot delete category 'Bills' because it contains 1 envelope"
        ):
            category_service.delete_category(session, "Bills")


class TestGetCategoriesWithEnvelopes:
    def test_hierarchical_view_with_balances(self, session):
        # Create categories
        category_service.create_category(session, name="Fixed Monthly Expenses", order_index=1)
        category_service.create_category(session, name="Wants", order_index=2)

        # Add cash funds (flows into existing Unassigned)
        envelope_service.add_to_cash(session, Decimal("1000.00"), source="Paycheck")

        # Create envelopes in categories
        envelope_service.create_envelope(
            session, EnvelopeBase(name="Rent"), category_name="Fixed Monthly Expenses"
        )
        envelope_service.create_envelope(
            session, EnvelopeBase(name="Dining Out"), category_name="Wants"
        )

        # Allocate funds
        envelope_service.assign_to_envelope(session, "Rent", Decimal("700.00"))
        envelope_service.assign_to_envelope(session, "Dining Out", Decimal("200.00"))

        grouped = category_service.get_categories_with_envelopes(session)

        cat_map = {g.name: g for g in grouped}
        assert "Fixed Monthly Expenses" in cat_map
        assert "Wants" in cat_map

        # Check total_balance calculation
        assert cat_map["Fixed Monthly Expenses"].total_balance == Decimal("700.00")
        assert cat_map["Wants"].total_balance == Decimal("200.00")

        # Check child envelopes
        fixed_envs = {e.name: e.balance for e in cat_map["Fixed Monthly Expenses"].envelopes}
        assert fixed_envs["Rent"] == Decimal("700.00")

        wants_envs = {e.name: e.balance for e in cat_map["Wants"].envelopes}
        assert wants_envs["Dining Out"] == Decimal("200.00")

    def test_uncategorized_envelopes_grouped(self, session):
        category_service.create_category(session, name="Investments", order_index=1)
        # Envelope without category
        envelope_service.create_envelope(session, EnvelopeBase(name="Random Envelope"))

        grouped = category_service.get_categories_with_envelopes(session)
        uncat = next((g for g in grouped if g.name == "Uncategorized"), None)
        assert uncat is not None
        assert uncat.id is None
        assert any(e.name == "Random Envelope" for e in uncat.envelopes)
