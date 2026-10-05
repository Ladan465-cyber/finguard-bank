"""
Recalculates a user's behaviour baseline from their REAL transaction
history. This is what the fraud engine compares new transactions against,
so it must be derived from actual completed transactions -- never
hand-set.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, pstdev

from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionStatus
from app.models.behavior import UserBehaviorProfile


def refresh_behavior_profile(db: Session, user_id: str) -> UserBehaviorProfile:
    profile = db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user_id).first()
    if not profile:
        profile = UserBehaviorProfile(user_id=user_id)
        db.add(profile)

    completed = (
        db.query(Transaction)
        .filter(Transaction.sender_id == user_id, Transaction.status == TransactionStatus.completed)
        .order_by(Transaction.created_at.desc())
        .limit(200)  # cap for performance; recent history is most relevant
        .all()
    )

    if completed:
        amounts = [float(t.amount) for t in completed]
        profile.avg_transaction_amount = Decimal(str(round(mean(amounts), 2)))
        profile.max_transaction_amount = Decimal(str(round(max(amounts), 2)))
        profile.std_dev_amount = Decimal(str(round(pstdev(amounts), 2))) if len(amounts) > 1 else Decimal("0")

        sorted_amounts = sorted(amounts)
        low_idx = max(0, int(len(sorted_amounts) * 0.1))
        high_idx = min(len(sorted_amounts) - 1, int(len(sorted_amounts) * 0.9))
        profile.typical_min_amount = Decimal(str(round(sorted_amounts[low_idx], 2)))
        profile.typical_max_amount = Decimal(str(round(sorted_amounts[high_idx], 2)))

        hours = [t.created_at.hour for t in completed]
        hours_sorted = sorted(hours)
        profile.typical_start_hour = hours_sorted[max(0, int(len(hours_sorted) * 0.05))]
        profile.typical_end_hour = hours_sorted[min(len(hours_sorted) - 1, int(len(hours_sorted) * 0.95))]
        if profile.typical_end_hour <= profile.typical_start_hour:
            profile.typical_start_hour, profile.typical_end_hour = 8, 21

        recipients = {}
        cities = {}
        for t in completed:
            recipients[t.recipient_account_number] = recipients.get(t.recipient_account_number, 0) + 1
            if t.city:
                cities[t.city] = cities.get(t.city, 0) + 1

        profile.common_recipients = [r for r, c in recipients.items() if c >= 1][:20]
        profile.common_cities = [c for c, n in cities.items() if n >= 1][:10]
        profile.total_transactions = len(completed)

    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_count = (
        db.query(Transaction)
        .filter(Transaction.sender_id == user_id, Transaction.created_at >= cutoff)
        .count()
    )
    profile.transactions_last_24h = recent_count
    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile


def get_txns_last_24h(db: Session, user_id: str) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return (
        db.query(Transaction)
        .filter(Transaction.sender_id == user_id, Transaction.created_at >= cutoff)
        .count()
    )


def get_txns_in_velocity_window(db: Session, user_id: str, minutes: int) -> int:
    """Counts transactions in a short recent window, used for the
    Transaction Context layer's HIGH_VELOCITY flag (many rapid transfers)."""
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(Transaction)
        .filter(Transaction.sender_id == user_id, Transaction.created_at >= cutoff)
        .count()
    )
