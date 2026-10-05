import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TransactionType(str, enum.Enum):
    transfer = "transfer"
    bill_payment = "bill_payment"
    airtime = "airtime"
    withdrawal = "withdrawal"


class RiskLevel(str, enum.Enum):
    safe = "SAFE"
    caution = "CAUTION"
    verify = "VERIFY"
    high_risk = "HIGH_RISK"
    critical = "CRITICAL"


class TransactionStatus(str, enum.Enum):
    pending = "pending"                 # created, fraud check in progress
    awaiting_otp = "awaiting_otp"        # medium risk
    awaiting_verification = "awaiting_verification"  # high risk
    approved = "approved"
    completed = "completed"
    rejected = "rejected"
    blocked = "blocked"


class InvestigationStatus(str, enum.Enum):
    none = "none"
    open = "open"
    reviewing = "reviewing"
    confirmed_fraud = "confirmed_fraud"
    confirmed_legitimate = "confirmed_legitimate"
    closed = "closed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    reference = Column(String(30), unique=True, nullable=False, index=True)

    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    sender_account_number = Column(String(10), nullable=False)

    recipient_account_number = Column(String(10), nullable=False)
    recipient_name = Column(String(150), nullable=True)
    recipient_bank = Column(String(100), nullable=True)

    amount = Column(Numeric(18, 2), nullable=False)
    transaction_type = Column(Enum(TransactionType), default=TransactionType.transfer)
    narration = Column(String(255), nullable=True)

    # Context captured at the moment of the transaction attempt
    device_fingerprint = Column(String(255), nullable=True)
    browser = Column(String(100), nullable=True)
    operating_system = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Fraud engine output
    risk_level = Column(Enum(RiskLevel, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    risk_factors = Column(JSON, nullable=True)          # list[str]
    fraud_rule_version = Column(String(20), nullable=True)

    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False)
    investigation_status = Column(Enum(InvestigationStatus), default=InvestigationStatus.none)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="transactions_sent")
    fraud_events = relationship("FraudEvent", back_populates="transaction", cascade="all, delete-orphan")
    verification_attempts = relationship("VerificationAttempt", back_populates="transaction", cascade="all, delete-orphan")
