from typing import List
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, SQLModel

from budget_app.db import get_session
from budget_app.schemas import (
    TransactionRequest, 
    TransactionResponse, 
    FinancedTransaction,
    TransactionType,
    TransactionDetailResponse,
    TransactionUpdateRequest,
    FinancedTransactionUpdateRequest,
    BalanceAdjustmentRequest
)
from budget_app.models import Transaction
from budget_app.services import (
    add_reg_transaction, 
    add_financed_transaction,
    get_transactions,
    delete_transaction,
    get_transaction_by_id,
    update_transaction,
    update_financed_transaction,
    make_payment,
    adjust_account_balance
)

class PaymentRequest(SQLModel):
    account: str
    amount: Decimal

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/regular", 
             response_model=TransactionResponse,
             status_code=status.HTTP_201_CREATED
)
def add_regular_transaction(
    transaction: TransactionRequest, 
    session: Session = Depends(get_session)
):
    try:
        master_tx: Transaction = add_reg_transaction(session, transaction)

        tx_id = master_tx.id
        if not tx_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Could not fetch new regular transaction"
            )
        
        return get_transaction_by_id(session, tx_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/financed", 
             response_model=TransactionResponse,
             status_code=status.HTTP_201_CREATED)
def add_fin_transaction(
    transaction: FinancedTransaction,
    session: Session = Depends(get_session)
):
    try:
        master_tx: Transaction = add_financed_transaction(session, transaction)

        tx_id = master_tx.id
        if not tx_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Could not fetch new financed transaction"
            )

        return get_transaction_by_id(session, tx_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[TransactionResponse])
def get_trans(
    limit: int | None = None,
    envelope: str | None = None,
    account: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    transaction_type: List[TransactionType] | None = Query(default=None),
    include_reversed: bool = False,
    session: Session = Depends(get_session)
):
    try:
        return get_transactions(
            session=session,
            limit=limit,
            envelope=envelope,
            account=account,
            date_from=date_from,
            date_to=date_to,
            transaction_type=transaction_type,
            include_reversed=include_reversed
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{id}", response_model=TransactionResponse)
def del_transaction(
    id: int,
    session: Session = Depends(get_session)
):
    try:
        master_tx = delete_transaction(
            session=session, 
            transaction_id=id
        )

        tx_id = master_tx.id
        if not tx_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Could not fetch reversal transaction"
            )

        return get_transaction_by_id(session, tx_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{id}", response_model=TransactionDetailResponse)
def get_trans_by_id(
    id: int, 
    session: Session = Depends(get_session)
):
    try:
        return get_transaction_by_id(
            session=session,
            transaction_id=id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/regular/{id}", response_model=TransactionResponse)
def update_reg_trans(
    id: int,
    updates: TransactionUpdateRequest,
    session: Session = Depends(get_session)
):
    try:
        master_tx = update_transaction(
            session=session, 
            transaction_id=id, 
            updates=updates
        )

        tx_id = master_tx.id
        if not tx_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Could not fetch updated transaction"
            )

        return get_transaction_by_id(session, tx_id)            
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/financed/{id}", response_model=TransactionResponse)
def update_fin_trans(
    id: int, 
    updates: FinancedTransactionUpdateRequest,
    session: Session = Depends(get_session)
):
    try:
        master_tx = update_financed_transaction(
            session=session,
            transaction_id=id,
            updates=updates
        )
        if not master_tx.id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Could not fetch updated transaction"
            )
        return get_transaction_by_id(session, master_tx.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post(
        "/payments", 
        response_model=List[TransactionResponse],
        status_code=status.HTTP_201_CREATED
)
def acct_payment(
    payload: PaymentRequest,
    session: Session = Depends(get_session)
):
    try:
        tx_list = make_payment(
            session=session,
            target=payload.account,
            amount=payload.amount
        )
        return [get_transaction_by_id(session, tx.id) for tx in tx_list if tx.id is not None]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/account-adjustment", 
             response_model=TransactionResponse | dict[str, str],
             status_code=status.HTTP_201_CREATED
)
def adjust_acct_bal(
    payload: BalanceAdjustmentRequest,
    session: Session = Depends(get_session)
):
    try:
        result: Transaction | None = adjust_account_balance(
            session=session,
            account_name=payload.account_name,
            target_balance=payload.target_balance,
            note=payload.note,
            envelope_name=payload.envelope_name
        )
        if not result:
            return {"message": "Account balance already matches"}

        if not result.id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch adjustment transaction"
            )

        return get_transaction_by_id(session, result.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
