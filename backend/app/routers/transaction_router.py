from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction_schemas import (
    TransactionCreate, TransactionResult, TransactionOut, OTPVerifyRequest, FacialVerifyRequest
)
from app.services import transaction_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResult)
def create_transaction(payload: TransactionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = transaction_service.create_and_assess_transaction(db, current_user, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return TransactionResult(
        transaction_id=result["transaction_id"],
        reference=result["reference"],
        status=result["status"],
        risk_level=result.get("risk_level"),
        customer_message=result["customer_message"],
        requires_otp=result.get("requires_otp", False),
        requires_verification=result.get("requires_verification", False),
    )


@router.get("/history", response_model=List[TransactionOut])
def history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns = (
        db.query(Transaction)
        .filter(Transaction.sender_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
        .all()
    )
    return txns


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.sender_id == current_user.id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    return txn


@router.post("/verify/otp")
def verify_otp(payload: OTPVerifyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return transaction_service.confirm_otp(db, current_user, payload.transaction_id, payload.otp_code)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/verify/facial")
def verify_facial(payload: FacialVerifyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return transaction_service.confirm_facial_verification(
            db, current_user, payload.transaction_id, payload.descriptor
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
