import random
import string

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, AdminUser, UserStatus
from app.models.account import Account
from app.schemas.auth_schemas import UserRegister, UserLogin, AdminLogin, TokenResponse, UserProfileOut
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.services.transaction_service import register_or_touch_device
from app.services import audit_service
from app.models.device import LoginSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _gen_account_number() -> str:
    return "".join(random.choices(string.digits, k=10))


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "An account with this email already exists")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "An account with this phone number already exists")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        home_city=payload.home_city,
        status=UserStatus.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    account = Account(user_id=user.id, account_number=_gen_account_number(), balance=50000)
    db.add(account)
    db.commit()

    token = create_access_token(subject=user.id, role="customer")
    audit_service.log_event(db, actor_type="user", actor_id=user.id, action="REGISTER")
    return TokenResponse(access_token=token, user_id=user.id, full_name=user.full_name)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            audit_service.log_event(db, actor_type="user", actor_id=user.id, action="LOGIN_FAILED")
        raise HTTPException(401, "Invalid email or password")

    if user.status != UserStatus.active:
        raise HTTPException(403, "This account is currently restricted. Please contact support.")

    register_or_touch_device(db, user.id, payload.device_fingerprint, payload.browser, payload.operating_system)

    session = LoginSession(
        user_id=user.id,
        device_fingerprint=payload.device_fingerprint,
        ip_address=request.client.host if request.client else None,
        city=payload.city,
        country=payload.country,
        success=True,
    )
    db.add(session)
    db.commit()

    token = create_access_token(subject=user.id, role="customer")
    audit_service.log_event(db, actor_type="user", actor_id=user.id, action="LOGIN_SUCCESS")
    return TokenResponse(access_token=token, user_id=user.id, full_name=user.full_name)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(401, "Invalid admin credentials")
    token = create_access_token(subject=admin.id, role=admin.role.value)
    audit_service.log_event(db, actor_type="admin", actor_id=admin.id, action="ADMIN_LOGIN_SUCCESS")
    return TokenResponse(access_token=token, user_id=admin.id, full_name=admin.full_name)


@router.get("/me", response_model=UserProfileOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
