from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.account import Account
from app.models.device import Device
from app.models.user import User
from app.schemas.transaction_schemas import FaceEnrollRequest
from app.services import face_service

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("/balance")
def get_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    return {
        "account_number": account.account_number,
        "bank_name": account.bank_name,
        "balance": str(account.balance),
        "currency": account.currency,
    }


@router.get("/devices")
def get_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.user_id == current_user.id).order_by(Device.last_seen_at.desc()).all()
    return [
        {
            "id": d.id,
            "device_name": d.device_name or f"{d.operating_system or 'Unknown OS'} · {d.browser or 'Unknown browser'}",
            "browser": d.browser,
            "operating_system": d.operating_system,
            "is_trusted": d.is_trusted,
            "first_seen_at": d.first_seen_at,
            "last_seen_at": d.last_seen_at,
            "times_used": d.times_used,
        }
        for d in devices
    ]
@router.get("/face-status")
def face_status(current_user: User = Depends(get_current_user)):
    return {"enrolled": current_user.face_descriptor is not None}


@router.post("/face-enroll")
def face_enroll(payload: FaceEnrollRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.face_descriptor:
        raise HTTPException(403, "Face ID is already enrolled and cannot be changed.")
    current_user.face_descriptor = payload.descriptor
    db.commit()
    return {"success": True, "enrolled": True}