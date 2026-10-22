"""Envelope category repository for database operations on EnvelopeCategory entity."""

from typing import List, Optional

from sqlmodel import Session, col, func, select

from budget_app.models import Envelope, EnvelopeCategory
from budget_app.schemas import EnvelopeCategoryBase


def get_category_by_id(session: Session, category_id: int) -> EnvelopeCategory | None:
    """Fetches a category by its primary key ID.

    Args:
        session: Active SQLModel database session.
        category_id: Integer ID of the category.

    Returns:
        The matching EnvelopeCategory instance if found, otherwise None.
    """
    stmt = select(EnvelopeCategory).where(EnvelopeCategory.id == category_id)
    return session.exec(stmt).one_or_none()


def get_category_by_name(session: Session, name: str) -> EnvelopeCategory | None:
    """Fetches a category by its unique name.

    Args:
        session: Active SQLModel database session.
        name: Name of the category to look up.

    Returns:
        The matching EnvelopeCategory instance if found, otherwise None.
    """
    stmt = select(EnvelopeCategory).where(EnvelopeCategory.name == name)
    return session.exec(stmt).one_or_none()


def create_category(session: Session, category_data: EnvelopeCategoryBase) -> EnvelopeCategory:
    """Strictly creates a new envelope category, raising an error if it already exists.

    Args:
        session: Active SQLModel database session.
        category_data: EnvelopeCategoryBase schema containing category details.

    Returns:
        The newly created EnvelopeCategory staged in the session.

    Raises:
        ValueError: If a category with the given name already exists.
    """
    existing = get_category_by_name(session, category_data.name)
    if existing:
        raise ValueError("Category already exists")

    category = EnvelopeCategory.model_validate(category_data)
    session.add(category)
    return category


def get_or_create_category(
    session: Session, category_data: EnvelopeCategoryBase
) -> EnvelopeCategory:
    """Retrieves an existing category by name, or creates and stages a new one if not found.

    Args:
        session: Active SQLModel database session.
        category_data: EnvelopeCategoryBase schema with name and attributes.

    Returns:
        The existing or newly staged EnvelopeCategory instance.
    """
    existing = get_category_by_name(session, category_data.name)
    if existing:
        return existing

    category = EnvelopeCategory.model_validate(category_data)
    session.add(category)
    return category


def get_categories(
    session: Session, is_active: Optional[bool] = None
) -> List[EnvelopeCategory]:
    """Fetches envelope categories from the database, ordered by order_index and name.

    Args:
        session: Active SQLModel database session.
        is_active: Optional boolean filter. If None, returns all categories.

    Returns:
        List of matching EnvelopeCategory instances ordered by order_index, then name.
    """
    stmt = select(EnvelopeCategory)
    if is_active is not None:
        stmt = stmt.where(EnvelopeCategory.is_active == is_active)

    stmt = stmt.order_by(col(EnvelopeCategory.order_index), col(EnvelopeCategory.name))
    return list(session.exec(stmt).all())


def count_envelopes_in_category(session: Session, category_id: int) -> int:
    """Counts the number of envelopes assigned to a category.

    Args:
        session: Active SQLModel database session.
        category_id: Integer ID of the category.

    Returns:
        Count of envelopes assigned to the category.
    """
    stmt = select(func.count(col(Envelope.id))).where(Envelope.category_id == category_id)
    return session.exec(stmt).one() or 0


def delete_category(session: Session, category: EnvelopeCategory) -> None:
    """Deletes an EnvelopeCategory entity from the session.

    Args:
        session: Active SQLModel database session.
        category: EnvelopeCategory instance to delete.
    """
    session.delete(category)
