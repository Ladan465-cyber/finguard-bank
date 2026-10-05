import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, JSON, Boolean, Text, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class FraudEventStatus(str, enum.Enum):
    open = "open"
    reviewing = "reviewing"
    resolved_fraud = "resolved_fraud"
    resolved_legitimate = "resolved_legitimate"


class FraudEvent(Base):
    """
    Created whenever a transaction is flagged MEDIUM risk or above.
    This is what powers the admin 'Fraud Alerts' feed.
    """
    __tablename__ = "fraud_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    risk_level = Column(String(20), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=True)  # not used by the v2 categorical engine; kept for schema compatibility
    risk_factors = Column(JSON, nullable=False)
    fraud_rule_version = Column(String(20), nullable=True)

    status = Column(Enum(FraudEventStatus), default=FraudEventStatus.open)
    reviewed_by_admin_id = Column(String(36), ForeignKey("admin_users.id"), nullable=True)
    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="fraud_events")


class FraudRule(Base):
    """
    Configurable weights/thresholds for the rule-based engine, stored in
    the DB (rather than hardcoded) so an admin could tune them without a
    redeploy, and so the engine's decisions are auditable against the
    exact rule set that produced them (fraud_rule_version).
    """
    __tablename__ = "fraud_rules"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    rule_key = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=False)
    weight = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    version = Column(String(20), default="1.0.0")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VerificationMethod(str, enum.Enum):
    otp = "otp"
    facial_simulation = "facial_simulation"


class VerificationResult(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    expired = "expired"


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    method = Column(Enum(VerificationMethod), nullable=False)
    code_hash = Column(String(255), nullable=True)   # hashed OTP, never stored/sent in plaintext to logs
    result = Column(Enum(VerificationResult), default=VerificationResult.pending)
    attempts_made = Column(String(5), default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="verification_attempts")
