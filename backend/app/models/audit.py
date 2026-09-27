import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    """
    Append-only trail of security-relevant events: logins, OTP attempts,
    admin actions on fraud alerts, transaction status changes, etc.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor_type = Column(String(20), nullable=False)   # 'user' | 'admin' | 'system'
    actor_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)       # e.g. 'LOGIN_SUCCESS', 'TX_BLOCKED'
    entity_type = Column(String(50), nullable=True)    # e.g. 'transaction'
    entity_id = Column(String(36), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
