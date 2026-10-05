import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, Integer, ForeignKey

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class BeneficiaryRiskCategory(str, enum.Enum):
    trusted = "TRUSTED"          # explicitly allow-listed (e.g. verified merchant)
    watchlisted = "WATCHLISTED"  # flagged for caution, not yet confirmed fraud
    high_risk = "HIGH_RISK"      # confirmed/strong fraud association
    # Note: there is no "unknown" stored value -- an account with no row in
    # this table simply defaults to UNKNOWN at query time. Only accounts
    # worth remembering something about get a row here.


class BeneficiaryRiskProfile(Base):
    """
    Fraud intelligence about a RECIPIENT account -- separate from anything
    about the sender. This is what powers the OPay-style pre-submit warning
    modal and the admin Beneficiary Watchlist screen.
    """
    __tablename__ = "beneficiary_risk_profiles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    account_number = Column(String(10), unique=True, nullable=False, index=True)
    risk_category = Column(Enum(BeneficiaryRiskCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    tags = Column(JSON, default=list)          # e.g. ["ponzi_scheme", "mule_account"]
    reason = Column(Text, nullable=True)        # human-readable explanation for admins/customers
    fraud_report_count = Column(Integer, default=0)
    complaint_count = Column(Integer, default=0)
    added_by_admin_id = Column(String(36), ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
