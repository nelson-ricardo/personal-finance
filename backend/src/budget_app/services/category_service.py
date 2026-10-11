"""Envelope category management service.

Handles:
- Creating envelope category groups (e.g. Fixed Monthly Expenses, Variable Monthly Expenses).
- Updating category name, display order, and active status.
- Deleting empty categories with relational integrity enforcement.
- Generating hierarchical category views with rolled-up balances and child envelopes.
"""

from decimal import Decimal
from typing import List, Optional

from sqlmodel import Session

from budget_app.models import EnvelopeCategory
from budget_app.repositories import category_repo, envelope_repo
from budget_app.schemas import (
    EnvelopeCategoryBase,
    EnvelopeCategoryUpdate,
    EnvelopeCategoryWithEnvelopes,
    EnvelopeWithBalance,
)


def create_category(
    session: Session, name: str, order_index: int = 0
) -> EnvelopeCategory:
    """Creates a new envelope category and persists it in the database.

    Args:
        session: Active SQLModel database session.
        name: Name of the category group.
        order_index: Display ordering index.

    Returns:
        The newly created EnvelopeCategory instance.

    Raises:
        ValueError: If name is empty/whitespace or already exists.
    """
    if not name or not name.strip():
        raise ValueError("Category name cannot be empty")

    name = name.strip()

    category = category_repo.create_category(
        session,
        EnvelopeCategoryBase(name=name, order_index=order_index, is_active=True),
    )
    session.commit()
    session.refresh(category)
    return category


def get_category_by_name(session: Session, name: str) -> EnvelopeCategory:
    """Fetches a category by its name, raising an error if not found.

    Args:
        session: Active SQLModel database session.
        name: Name of the category.

    Returns:
        The matching EnvelopeCategory instance.

    Raises:
        ValueError: If name is empty/whitespace or category does not exist.
    """
    if not name or not name.strip():
        raise ValueError("Category name cannot be empty")

    name = name.strip()
    category = category_repo.get_category_by_name(session, name)
    if not category:
        raise ValueError(f"Category '{name}' does not exist")

    return category


def get_category_by_id(session: Session, category_id: int) -> EnvelopeCategory:
    """Fetches a category by its primary key ID, raising an error if not found.

    Args:
        session: Active SQLModel database session.
        category_id: Integer ID of the category.

    Returns:
        The matching EnvelopeCategory instance.

    Raises:
        ValueError: If category does not exist.
    """
    category = category_repo.get_category_by_id(session, category_id)
    if not category:
        raise ValueError(f"Category ID {category_id} does not exist")

    return category


def get_categories(
    session: Session, is_active: Optional[bool] = None
) -> List[EnvelopeCategory]:
    """Retrieves all envelope categories, ordered by order_index and name."""
    return category_repo.get_categories(session, is_active=is_active)


def update_category(
    session: Session, category_name: str, update_data: EnvelopeCategoryUpdate
) -> EnvelopeCategory:
    """Updates the name, order_index, or active status of a category.

    Args:
        session: Active SQLModel database session.
        category_name: Current name of the category to update.
        update_data: Payload with fields to update.

    Returns:
        The updated EnvelopeCategory instance.

    Raises:
        ValueError: If category does not exist, new name is empty or already taken.
    """
    category = get_category_by_name(session, category_name)

    if update_data.name is not None:
        new_name = update_data.name.strip()
        if not new_name:
            raise ValueError("Category name cannot be empty")
        if new_name != category.name:
            existing = category_repo.get_category_by_name(session, new_name)
            if existing:
                raise ValueError(f"Category '{new_name}' already exists")
            category.name = new_name

    if update_data.order_index is not None:
        category.order_index = update_data.order_index

    if update_data.is_active is not None:
        category.is_active = update_data.is_active

    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def delete_category(session: Session, category_name: str) -> None:
    """Deletes an envelope category if it has no assigned envelopes.

    Args:
        session: Active SQLModel database session.
        category_name: Name of the category to delete.

    Raises:
        ValueError: If category does not exist or has assigned envelopes.
    """
    category = get_category_by_name(session, category_name)

    if category.id is not None:
        envelope_count = category_repo.count_envelopes_in_category(session, category.id)
        if envelope_count > 0:
            raise ValueError(
                f"Cannot delete category '{category_name}' because it contains {envelope_count} envelope(s). "
                "Please reassign or remove them first."
            )

    category_repo.delete_category(session, category)
    session.commit()


def get_categories_with_envelopes(
    session: Session, is_active: Optional[bool] = None
) -> List[EnvelopeCategoryWithEnvelopes]:
    """Retrieves all categories with their child envelopes and rolled-up total balances.

    If any envelopes are uncategorized (category_id is None), an 'Uncategorized'
    group is included at the end.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter for active status.

    Returns:
        List of EnvelopeCategoryWithEnvelopes instances.
    """
    categories = category_repo.get_categories(session, is_active=is_active)
    result: List[EnvelopeCategoryWithEnvelopes] = []

    for cat in categories:
        envelopes = envelope_repo.get_envelopes_by_category(
            session, category_id=cat.id, is_active=is_active
        )
        cat_total = Decimal("0.00")
        envelope_items: List[EnvelopeWithBalance] = []

        for env in envelopes:
            bal = envelope_repo.get_balance_for_envelope(session, env)
            cat_total += bal
            envelope_items.append(
                EnvelopeWithBalance(
                    id=env.id,
                    name=env.name,
                    note=env.note,
                    is_active=env.is_active,
                    category_id=cat.id,
                    category_name=cat.name,
                    system_role=env.system_role,
                    balance=bal,
                )
            )

        result.append(
            EnvelopeCategoryWithEnvelopes(
                id=cat.id,
                name=cat.name,
                order_index=cat.order_index,
                is_active=cat.is_active,
                total_balance=cat_total,
                envelopes=envelope_items,
            )
        )

    # Check for uncategorized envelopes
    uncategorized_envs = envelope_repo.get_envelopes_by_category(
        session, category_id=None, is_active=is_active
    )
    if uncategorized_envs:
        uncat_total = Decimal("0.00")
        uncat_items: List[EnvelopeWithBalance] = []

        for env in uncategorized_envs:
            bal = envelope_repo.get_balance_for_envelope(session, env)
            uncat_total += bal
            uncat_items.append(
                EnvelopeWithBalance(
                    id=env.id,
                    name=env.name,
                    note=env.note,
                    is_active=env.is_active,
                    category_id=None,
                    category_name=None,
                    system_role=env.system_role,
                    balance=bal,
                )
            )

        result.append(
            EnvelopeCategoryWithEnvelopes(
                id=None,
                name="Uncategorized",
                order_index=9999,
                is_active=True,
                total_balance=uncat_total,
                envelopes=uncat_items,
            )
        )

    return result
