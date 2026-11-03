"""API routes for obligations (bills, credit cards, loans)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from budget_app.db import get_session
from budget_app.schemas.obligation import (
    ObligationCreate,
    ObligationMarkPaidRequest,
    ObligationResponse,
    ObligationUpdate,
)
from budget_app.services import obligation_service

router = APIRouter(prefix="/obligations", tags=["obligations"])


@router.get("/", response_model=List[ObligationResponse], status_code=status.HTTP_200_OK)
def get_obligations(
    is_active: Optional[bool] = Query(default=None),
    session: Session = Depends(get_session),
):
    """Retrieves all obligations sorted by due day with computed calendar status."""
    return obligation_service.get_all_obligations(session, is_active=is_active)


@router.get("/{obligation_id}", response_model=ObligationResponse, status_code=status.HTTP_200_OK)
def get_obligation(
    obligation_id: int,
    session: Session = Depends(get_session),
):
    """Retrieves a single obligation by ID."""
    obl = obligation_service.get_obligation_by_id(session, obligation_id)
    if not obl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Obligation with ID {obligation_id} not found",
        )
    return obl


@router.post("/", response_model=ObligationResponse, status_code=status.HTTP_201_CREATED)
def create_obligation(
    payload: ObligationCreate,
    session: Session = Depends(get_session),
):
    """Creates a new obligation."""
    return obligation_service.create_obligation(session, payload)


@router.patch("/{obligation_id}", response_model=ObligationResponse, status_code=status.HTTP_200_OK)
def update_obligation(
    obligation_id: int,
    payload: ObligationUpdate,
    session: Session = Depends(get_session),
):
    """Updates an existing obligation."""
    updated = obligation_service.update_obligation(session, obligation_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Obligation with ID {obligation_id} not found",
        )
    return updated


@router.delete("/{obligation_id}", status_code=status.HTTP_200_OK)
def delete_obligation(
    obligation_id: int,
    session: Session = Depends(get_session),
) -> Dict[str, bool]:
    """Deletes an obligation."""
    deleted = obligation_service.delete_obligation(session, obligation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Obligation with ID {obligation_id} not found",
        )
    return {"deleted": True}


@router.post("/{obligation_id}/pay", response_model=ObligationResponse, status_code=status.HTTP_200_OK)
def mark_paid(
    obligation_id: int,
    payload: ObligationMarkPaidRequest,
    session: Session = Depends(get_session),
):
    """Marks an obligation as paid or unpaid for the current billing cycle."""
    updated = obligation_service.mark_obligation_paid(session, obligation_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Obligation with ID {obligation_id} not found",
        )
    return updated


@router.post("/sync-accounts", status_code=status.HTTP_200_OK)
def sync_accounts(
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Scans all active Credit Card and Loan accounts with due dates and syncs them to obligations."""
    return obligation_service.sync_obligations_from_accounts(session)
