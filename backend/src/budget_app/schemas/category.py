"""Envelope category data schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlmodel import Field, SQLModel

from budget_app.schemas.envelope import EnvelopeWithBalance


class EnvelopeCategoryBase(SQLModel):
    """Base schema defining properties for an envelope category group."""

    name: str = Field(unique=True, description="Unique display name of the category group")
    order_index: int = Field(default=0, description="Display order index for UI/presentation")
    is_active: bool = Field(default=True, description="Flag indicating whether this category group is active")


class EnvelopeCategoryCreate(EnvelopeCategoryBase):
    """Payload for creating a new envelope category."""

    pass


class EnvelopeCategoryUpdate(SQLModel):
    """Payload for updating an envelope category."""

    name: Optional[str] = Field(default=None, description="Updated name of the category")
    order_index: Optional[int] = Field(default=None, description="Updated display order index")
    is_active: Optional[bool] = Field(default=None, description="Updated active status")


class EnvelopeCategoryResponse(EnvelopeCategoryBase):
    """Response schema for an envelope category with its primary key ID."""

    id: int = Field(description="Primary key ID of the category group")


class EnvelopeCategoryWithEnvelopes(SQLModel):
    """Hierarchical grouping of a category, its child envelopes, and the total category balance."""

    id: Optional[int] = Field(default=None, description="Primary key ID (None for Uncategorized group)")
    name: str = Field(description="Category name (or 'Uncategorized')")
    order_index: int = Field(default=0, description="Display order index")
    is_active: bool = Field(default=True, description="Active status")
    total_balance: Decimal = Field(default=Decimal("0.00"), description="Sum of all child envelope balances")
    envelopes: List[EnvelopeWithBalance] = Field(
        default_factory=list, description="Envelopes belonging to this category"
    )
