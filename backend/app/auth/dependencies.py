from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.security import decode_access_token
from app.models.user import User, AdminUser

oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _unauthorized(msg: str = "Could not validate credentials"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg,
                          headers={"WWW-Authenticate": "Bearer"})


def get_current_user(token: str = Depends(oauth2_scheme_user), db: Session = Depends(get_db)) -> User:
    if not token:
        raise _unauthorized("Not authenticated")
    payload = decode_access_token(token)
    if not payload or payload.get("role") != "customer":
        raise _unauthorized()
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise _unauthorized("User not found")
    return user


def get_current_admin(token: str = Depends(oauth2_scheme_user), db: Session = Depends(get_db)) -> AdminUser:
    if not token:
        raise _unauthorized("Not authenticated")
    payload = decode_access_token(token)
    if not payload or payload.get("role") not in ("fraud_analyst", "super_admin"):
        raise _unauthorized("Admin access required")
    admin = db.query(AdminUser).filter(AdminUser.id == payload["sub"]).first()
    if not admin:
        raise _unauthorized("Admin not found")
    return admin
