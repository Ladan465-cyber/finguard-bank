"""
Fraud Detection Engine
=======================

A transparent, rule/behaviour-based risk engine. Every rule inspects the
INCOMING transaction against the user's REAL stored behaviour profile and
history (never random, never a single hardcoded 'this one is fraud' check).

Architecture note (see documentation/ML_ROADMAP.md):
This module intentionally exposes `extract_features()` separately from
`score_transaction()`. That split is what lets this rule engine be swapped
for a trained model later:

    historical data -> extract_features() -> [ML model] -> fraud_probability
                                            -> decision_engine() -> action

For the hackathon, `score_transaction()` acts as the "model": it converts
features into a 0-100 risk score using weighted rules pulled from the
`fraud_rules` table (so the weights are configurable, not buried in code).
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.behavior import UserBehaviorProfile
from app.models.transaction import Transaction, RiskLevel
from app.models.device import Device
from app.models.fraud import FraudRule


# ---------------------------------------------------------------------
# Default rule weights (seeded into fraud_rules table; editable there)
# ---------------------------------------------------------------------
DEFAULT_RULE_WEIGHTS = {
    "amount_moderately_above_normal": 15,   # 2x-4x avg
    "amount_significantly_above_normal": 30,  # 4x-8x avg
    "amount_extreme": 45,                    # >8x avg or > max ever
    "new_recipient": 12,
    "new_device": 20,
    "unusual_location": 18,
    "unusual_country": 35,
    "unusual_time": 10,
    "high_frequency": 15,                    # many txns in short window
    "amount_near_balance_limit": 10,
    "multiple_anomaly_combo_bonus": 15,       # 3+ triggers together
}


@dataclass
class FeatureSet:
    amount: Decimal
    avg_amount: Decimal
    max_amount: Decimal
    typical_min: Decimal
    typical_max: Decimal
    is_new_recipient: bool
    is_new_device: bool
    is_unusual_city: bool
    is_unusual_country: bool
    is_unusual_time: bool
    hour_of_day: int
    txns_last_24h: int
    is_high_frequency: bool
    amount_ratio_to_avg: float
    balance_utilisation_pct: float


@dataclass
class RiskAssessment:
    score: float                      # 0-100
    level: RiskLevel
    triggered_factors: List[str] = field(default_factory=list)
    rule_version: str = "1.0.0"


def _get_active_weights(db: Session) -> dict:
    rows = db.query(FraudRule).filter(FraudRule.is_active == True).all()  # noqa: E712
    if not rows:
        return DEFAULT_RULE_WEIGHTS
    return {r.rule_key: float(r.weight) for r in rows}


def extract_features(
    db: Session,
    profile: Optional[UserBehaviorProfile],
    amount: Decimal,
    recipient_account_number: str,
    device_fingerprint: str,
    city: Optional[str],
    country: Optional[str],
    user_id: str,
    account_balance: Decimal,
    simulated_hour: Optional[int] = None,
    txns_last_24h: int = 0,
) -> FeatureSet:
    """Turn raw transaction + stored history into comparable features."""

    now_hour = simulated_hour if simulated_hour is not None else datetime.utcnow().hour

    if profile and profile.total_transactions and profile.total_transactions > 0:
        avg_amount = Decimal(profile.avg_transaction_amount or 0)
        max_amount = Decimal(profile.max_transaction_amount or 0)
        typical_min = Decimal(profile.typical_min_amount or 0)
        typical_max = Decimal(profile.typical_max_amount or 0)
        common_recipients = profile.common_recipients or []
        common_cities = profile.common_cities or []
        home_country = profile.home_country or "Nigeria"
        typical_start = profile.typical_start_hour if profile.typical_start_hour is not None else 8
        typical_end = profile.typical_end_hour if profile.typical_end_hour is not None else 21
    else:
        # Brand-new user with no history: treat everything as baseline
        # (first transaction can't be judged against a history that
        # doesn't exist yet -- it is evaluated on absolute terms only).
        avg_amount = Decimal(0)
        max_amount = Decimal(0)
        typical_min = Decimal(0)
        typical_max = Decimal(0)
        common_recipients = []
        common_cities = []
        home_country = "Nigeria"
        typical_start, typical_end = 8, 21

    is_new_recipient = recipient_account_number not in common_recipients
    is_new_device = db.query(Device).filter(
        Device.user_id == user_id,
        Device.device_fingerprint == device_fingerprint,
        Device.is_trusted == True,  # noqa: E712
    ).first() is None

    is_unusual_city = bool(city) and city not in common_cities and len(common_cities) > 0
    is_unusual_country = bool(country) and country != home_country

    is_unusual_time = not (typical_start <= now_hour <= typical_end)

    is_high_frequency = txns_last_24h >= 5

    amount_ratio_to_avg = float(amount / avg_amount) if avg_amount and avg_amount > 0 else (
        2.0 if amount > 0 else 0.0  # new user: neutral-ish ratio, judged elsewhere
    )

    balance_utilisation_pct = float(amount / account_balance * 100) if account_balance and account_balance > 0 else 100.0

    return FeatureSet(
        amount=amount,
        avg_amount=avg_amount,
        max_amount=max_amount,
        typical_min=typical_min,
        typical_max=typical_max,
        is_new_recipient=is_new_recipient,
        is_new_device=is_new_device,
        is_unusual_city=is_unusual_city,
        is_unusual_country=is_unusual_country,
        is_unusual_time=is_unusual_time,
        hour_of_day=now_hour,
        txns_last_24h=txns_last_24h,
        is_high_frequency=is_high_frequency,
        amount_ratio_to_avg=amount_ratio_to_avg,
        balance_utilisation_pct=balance_utilisation_pct,
    )


def score_transaction(db: Session, features: FeatureSet, rule_version: str = "1.0.0") -> RiskAssessment:
    weights = _get_active_weights(db)
    score = 0.0
    factors: List[str] = []

    has_history = features.avg_amount > 0

    # --- Amount deviation -------------------------------------------------
    if has_history:
        ratio = features.amount_ratio_to_avg
        if ratio >= 8 or (features.max_amount > 0 and features.amount > features.max_amount * Decimal("1.5")):
            score += weights.get("amount_extreme", 45)
            factors.append(
                f"Transaction amount is extremely above the user's normal range "
                f"({ratio:.1f}x average)"
            )
        elif ratio >= 4:
            score += weights.get("amount_significantly_above_normal", 30)
            factors.append(
                f"Transaction amount is significantly above the user's normal range "
                f"({ratio:.1f}x average)"
            )
        elif ratio >= 2:
            score += weights.get("amount_moderately_above_normal", 15)
            factors.append(
                f"Transaction amount is moderately above the user's normal range "
                f"({ratio:.1f}x average)"
            )
    else:
        # No history yet: flag only very large absolute first transactions
        if features.amount >= Decimal("300000"):
            score += weights.get("amount_significantly_above_normal", 30)
            factors.append("Large amount for a first-time transaction with no prior history")

    # --- New recipient ------------------------------------------------------
    if features.is_new_recipient:
        score += weights.get("new_recipient", 12)
        factors.append("New recipient detected (not in user's known recipient list)")

    # --- New device -----------------------------------------------------
    if features.is_new_device:
        score += weights.get("new_device", 20)
        factors.append("Transaction initiated from an unrecognised device")

    # --- Location -------------------------------------------------------
    if features.is_unusual_country:
        score += weights.get("unusual_country", 35)
        factors.append("Transaction originates from an unusual country for this user")
    elif features.is_unusual_city:
        score += weights.get("unusual_location", 18)
        factors.append("Transaction originates from a location not previously used by this user")

    # --- Time -------------------------------------------------------------
    if features.is_unusual_time:
        score += weights.get("unusual_time", 10)
        factors.append(f"Transaction occurred at an unusual time ({features.hour_of_day:02d}:00)")

    # --- Frequency ----------------------------------------------------------
    if features.is_high_frequency:
        score += weights.get("high_frequency", 15)
        factors.append(f"Abnormally high transaction frequency ({features.txns_last_24h} transactions in 24h)")

    # --- Balance utilisation --------------------------------------------
    if features.balance_utilisation_pct >= 90:
        score += weights.get("amount_near_balance_limit", 10)
        factors.append("Transaction amount consumes nearly all of the account balance")

    # --- Combo bonus: multiple independent anomalies compound risk -----
    if len(factors) >= 3:
        score += weights.get("multiple_anomaly_combo_bonus", 15)
        factors.append("Multiple independent risk indicators triggered simultaneously")

    score = min(score, 100.0)

    if score < 20:
        level = RiskLevel.low
    elif score < 45:
        level = RiskLevel.medium
    elif score < 75:
        level = RiskLevel.high
    else:
        level = RiskLevel.critical

    if not factors:
        factors.append("No anomalies detected — transaction matches user's established behaviour")

    return RiskAssessment(score=round(score, 2), level=level, triggered_factors=factors, rule_version=rule_version)
