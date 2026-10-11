from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from budget_app.db import get_session
from budget_app.schemas import (
    EnvelopeCategoryCreate,
    EnvelopeCategoryResponse,
    EnvelopeCategoryUpdate,
    EnvelopeCategoryWithEnvelopes,
)
from budget_app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=EnvelopeCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: EnvelopeCategoryCreate,
    session: Session = Depends(get_session),
):
    try:
        return category_service.create_category(
            session=session,
            name=payload.name,
            order_index=payload.order_index,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[EnvelopeCategoryResponse], status_code=status.HTTP_200_OK)
def get_categories(
    is_active: bool | None = None,
    session: Session = Depends(get_session),
):
    return category_service.get_categories(session=session, is_active=is_active)


@router.get(
    "/with-envelopes",
    response_model=List[EnvelopeCategoryWithEnvelopes],
    status_code=status.HTTP_200_OK,
)
def get_categories_with_envelopes(
    is_active: bool | None = None,
    session: Session = Depends(get_session),
):
    return category_service.get_categories_with_envelopes(session=session, is_active=is_active)


@router.get("/{name}", response_model=EnvelopeCategoryResponse, status_code=status.HTTP_200_OK)
def get_category(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        return category_service.get_category_by_name(session=session, name=name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{name}", response_model=EnvelopeCategoryResponse, status_code=status.HTTP_200_OK)
def update_category(
    name: str,
    payload: EnvelopeCategoryUpdate,
    session: Session = Depends(get_session),
):
    try:
        return category_service.update_category(
            session=session, category_name=name, update_data=payload
        )
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "does not exist" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/{name}", status_code=status.HTTP_200_OK)
def delete_category(
    name: str,
    session: Session = Depends(get_session),
):
    try:
        category_service.delete_category(session=session, category_name=name)
        return {"message": f"Category '{name}' deleted successfully"}
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "does not exist" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))
