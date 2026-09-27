import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Enum, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UserStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    locked = "locked"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.active, nullable=False)
    bvn_last4 = Column(String(4), nullable=True)  # demo-only, never store full BVN
    home_city = Column(String(100), nullable=True)
    home_country = Column(String(100), default="Nigeria")
    face_descriptor = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account", back_populates="user", uselist=False, cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    behavior_profile = relationship("UserBehaviorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions_sent = relationship("Transaction", foreign_keys="Transaction.sender_id", back_populates="sender")


class AdminRole(str, enum.Enum):
    fraud_analyst = "fraud_analyst"
    super_admin = "super_admin"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(AdminRole), default=AdminRole.fraud_analyst, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
