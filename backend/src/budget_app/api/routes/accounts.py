from typing import List

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import Session

from budget_app.db import get_session
from budget_app.schemas import AccountCreate, AccountResponse, AccountUpdate, AccountType
from budget_app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])

# create a single account
@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: AccountCreate, session: Session = Depends(get_session)):
    try:
        return account_service.create_account(session, account)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# get all accounts
@router.get("/", response_model=List[AccountResponse], status_code=status.HTTP_200_OK)
def get_accounts(
    is_active: bool | None = None,
    account_type: List[AccountType] | None = Query(default=None),
    session: Session = Depends(get_session)
):
    return account_service.get_all_accounts(
        session, is_active=is_active, account_types=account_type
    )

#get account by name
@router.get("/{name}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def get_account(name: str, session: Session = Depends(get_session)):
    ret_account: AccountResponse | None = account_service.get_account(session, name)
    if not ret_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Account {name} does not exist"
        )
    
    return ret_account

# update account metadata
@router.patch("/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def update_account(
    account_id: int,
    account_info: AccountUpdate, 
    session: Session = Depends(get_session)
):
    try:
        return account_service.update_account(session, account_id, account_info)
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "does not exist" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))

# archive account
@router.delete("/{name}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def delete_account(
    name: str,
    session: Session = Depends(get_session)
):
    try:
        return account_service.delete_account(session, name)
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "does not exist" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))

# reactivate account
@router.post("/{name}/activate", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def activate_account(
    name: str,
    session: Session = Depends(get_session)
):
    try:
        return account_service.activate_account(session, name)
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "does not exist" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))

