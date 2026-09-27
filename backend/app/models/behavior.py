import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UserBehaviorProfile(Base):
    """
    A rolling summary of each user's 'normal' behaviour, used by the fraud
    engine as the baseline to compare new transactions against.

    This is recalculated after every completed transaction (see
    services/behavior_service.py) so it always reflects genuine history
    rather than a static, hand-entered value.
    """
    __tablename__ = "user_behavior_profiles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    avg_transaction_amount = Column(Numeric(18, 2), default=0)
    max_transaction_amount = Column(Numeric(18, 2), default=0)
    std_dev_amount = Column(Numeric(18, 2), default=0)
    typical_min_amount = Column(Numeric(18, 2), default=0)
    typical_max_amount = Column(Numeric(18, 2), default=0)

    typical_start_hour = Column(Integer, default=8)   # 24h clock
    typical_end_hour = Column(Integer, default=21)

    common_recipients = Column(JSON, default=list)     # list[str] account numbers
    common_cities = Column(JSON, default=list)          # list[str]
    home_country = Column(String(100), default="Nigeria")

    total_transactions = Column(Integer, default=0)
    transactions_last_24h = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="behavior_profile")
