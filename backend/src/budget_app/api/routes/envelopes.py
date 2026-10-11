from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from budget_app.db import get_session
from budget_app.schemas import (
    CashIncomeRequest,
    EnvelopeAssignRequest,
    EnvelopeBase,
    EnvelopeCreate,
    EnvelopeTransfer,
    EnvelopeTransferRequest,
    EnvelopeUpdate,
    EnvelopeWithBalance,
    TransactionResponse,
)
from budget_app.services import envelope_service, transaction_service

router = APIRouter(prefix="/envelopes", tags=["envelopes"])


@router.post("/", response_model=EnvelopeWithBalance, status_code=status.HTTP_201_CREATED)
def create_envelope(
    payload: EnvelopeCreate,
    session: Session = Depends(get_session),
):
    try:
        envelope_base = EnvelopeBase(
            name=payload.name,
            note=payload.note,
            is_active=payload.is_active,
        )
        created = envelope_service.create_envelope(
            session=session,
            envelope_info=envelope_base,
            category_name=payload.category_name,
        )
        return envelope_service.get_single_envelope_w_balance(session, created.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[EnvelopeWithBalance], status_code=status.HTTP_200_OK)
def get_envelopes(
    is_active: bool | None = None,
    session: Session = Depends(get_session),
):
    return envelope_service.get_envelopes_and_balances(session=session, is_active=is_active)


@router.post("/transfer", response_model=EnvelopeTransfer, status_code=status.HTTP_200_OK)
def transfer_envelopes(
    payload: EnvelopeTransferRequest,
    session: Session = Depends(get_session),
):
    try:
        return envelope_service.transfer_between_envelopes(
            session=session,
            source=payload.source_envelope,
            destination=payload.destination_envelope,
            amount=payload.amount,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/assign", response_model=EnvelopeTransfer, status_code=status.HTTP_200_OK)
def assign_envelope(
    payload: EnvelopeAssignRequest,
    session: Session = Depends(get_session),
):
    try:
        return envelope_service.assign_to_envelope(
            session=session,
            destination=payload.envelope_name,
            amount=payload.amount,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/income", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def add_income_to_cash(
    payload: CashIncomeRequest,
    session: Session = Depends(get_session),
):
    try:
        master_tx = envelope_service.add_to_cash(
            session=session,
            amount=payload.amount,
            source=payload.source,
            note=payload.note,
        )
        if not master_tx.id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch created income transaction",
            )
        return transaction_service.get_transaction_by_id(session, master_tx.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{name}", response_model=EnvelopeWithBalance, status_code=status.HTTP_200_OK)
def get_envelope(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        return envelope_service.get_single_envelope_w_balance(session=session, envelope_name=name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{name}", response_model=EnvelopeWithBalance, status_code=status.HTTP_200_OK)
def update_envelope(
    name: str,
    payload: EnvelopeUpdate,
    session: Session = Depends(get_session),
):
    try:
        updated = envelope_service.update_envelope_info(
            session=session, target_name=name, envelope_info=payload
        )
        return envelope_service.get_single_envelope_w_balance(session=session, envelope_name=updated.name)
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "does not exist" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/{name}/activate", response_model=EnvelopeWithBalance, status_code=status.HTTP_200_OK)
def activate_envelope(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        activated = envelope_service.activate_envelope(session=session, envelope_name=name)
        return envelope_service.get_single_envelope_w_balance(session=session, envelope_name=activated.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{name}/deactivate", response_model=EnvelopeWithBalance, status_code=status.HTTP_200_OK)
def deactivate_envelope(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        deactivated = envelope_service.deactivate_envelope(session=session, envelope_name=name)
        return envelope_service.get_single_envelope_w_balance(
            session=session, envelope_name=deactivated.name
        )
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "does not exist" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/{name}", status_code=status.HTTP_200_OK)
def delete_envelope(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        envelope_service.perma_delete_envelope(session=session, envelope_name=name)
        return {"message": f"Envelope '{name}' deleted successfully"}
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "does not exist" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))
