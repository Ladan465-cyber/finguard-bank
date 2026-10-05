"""
FinShield Fraud Decision Engine (v2)
=====================================

This is a genuine multi-layer decision system, not a percentage/points
scorer. Each layer below independently produces a CATEGORY label (or a
list of named flags) describing what it observed -- never a number. The
Decision Engine at the bottom then reads all four layers' outputs together
through an explicit, ordered rule table (read top to bottom, first match
wins) to arrive at one of five outcomes: SAFE, CAUTION, VERIFY, HIGH_RISK,
CRITICAL.

This mirrors how real fraud/underwriting review actually works: a human
reviewer doesn't add up points, they ask "does any one thing here demand
escalation regardless of the others?" first, then combine softer signals
only if nothing already forced a decision.

    Customer Behaviour Analysis   -> NORMAL / LOW_CONCERN / MEDIUM_CONCERN / HIGH_CONCERN
    Device & Location Analysis    -> TRUSTED / REQUIRES_ATTENTION / SUSPICIOUS
    Transaction Context Analysis  -> a list of named flags (can be empty)
    Beneficiary Risk Analysis     -> TRUSTED / UNKNOWN / WATCHLISTED / HIGH_RISK
                                            |
                                            v
                                   Fraud Decision Engine (rule table)
                                            |
                                            v
                          SAFE / CAUTION / VERIFY / HIGH_RISK / CRITICAL

Architecture note for future ML integration (see documentation/ML_ROADMAP.md):
extract_features() still isolates raw feature extraction from the layer
classifiers and the decision table, so any individual layer's classifier
could later be swapped for a trained model without touching the others or
the decision table itself.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.behavior import UserBehaviorProfile
from app.models.transaction import Transaction, RiskLevel, TransactionStatus
from app.models.device import Device
from app.models.beneficiary import BeneficiaryRiskProfile


# ---------------------------------------------------------------------
# Tunable constants (named, not buried in a formula). These are the
# "dials" worth adjusting if real-world testing shows escalation
# happening too often or too rarely -- see documentation/DEMO_SCENARIOS.md.
# ---------------------------------------------------------------------
VELOCITY_WINDOW_MINUTES = 3
VELOCITY_TRANSACTION_THRESHOLD = 5      # this many transfers within the window = HIGH_VELOCITY
CONCERN_ESCALATION_COUNT = 2            # "2 or more other layers concerned" threshold for Rule 1/3


@dataclass
class FeatureSet:
    amount: Decimal
    avg_amount: Decimal
    max_amount: Decimal
    is_new_recipient: bool
    is_new_device: bool
    is_unusual_city: bool
    is_unusual_country: bool
    is_unusual_time: bool
    hour_of_day: int
    txns_last_24h: int
    txns_in_velocity_window: int
    amount_ratio_to_avg: float
    balance_utilisation_pct: float
    acknowledged_beneficiary_warning: bool
    median_amount: Decimal = Decimal(0)
    history_count: int = 0


@dataclass
class LayerResults:
    behaviour_tier: str
    device_location_tier: str
    context_flags: List[str]
    beneficiary_tier: str
    beneficiary_reason: Optional[str] = None


@dataclass
class RiskAssessment:
    level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    layers: Optional[LayerResults] = None
    rule_version: str = "2.0.0"


# ---------------------------------------------------------------------
# Feature extraction -- turns raw transaction + stored history into the
# comparable values each layer classifier needs. No decisions happen here.
# ---------------------------------------------------------------------
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
    txns_in_velocity_window: int = 0,
    acknowledged_beneficiary_warning: bool = False,
) -> FeatureSet:
    now_hour = simulated_hour if simulated_hour is not None else datetime.utcnow().hour

    if profile and profile.total_transactions and profile.total_transactions > 0:
        avg_amount = Decimal(profile.avg_transaction_amount or 0)
        max_amount = Decimal(profile.max_transaction_amount or 0)
        common_recipients = profile.common_recipients or []
        common_cities = profile.common_cities or []
        home_country = profile.home_country or "Nigeria"
        typical_start = profile.typical_start_hour if profile.typical_start_hour is not None else 8
        typical_end = profile.typical_end_hour if profile.typical_end_hour is not None else 21
    else:
        avg_amount = Decimal(0)
        max_amount = Decimal(0)
        common_recipients = []
        common_cities = []
        home_country = "Nigeria"
        typical_start, typical_end = 8, 21
    recent = (
        db.query(Transaction.amount)
        .filter(Transaction.sender_id == user_id, Transaction.status == TransactionStatus.completed)
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )
    amounts = sorted(float(r[0]) for r in recent)
    history_count = len(amounts)
    median_amount = Decimal(str(amounts[history_count // 2])) if amounts else Decimal(0)
    if amounts:
        max_amount = Decimal(str(amounts[-1]))

    baseline = median_amount if history_count >= 5 else avg_amount
    is_new_recipient = recipient_account_number not in common_recipients
    is_new_device = db.query(Device).filter(
        Device.user_id == user_id,
        Device.device_fingerprint == device_fingerprint,
        Device.is_trusted == True,  # noqa: E712
    ).first() is None

    is_unusual_city = bool(city) and city not in common_cities and len(common_cities) > 0
    is_unusual_country = bool(country) and country != home_country
    is_unusual_time = not (typical_start <= now_hour <= typical_end)

    amount_ratio_to_avg = float(amount / baseline) if baseline and baseline > 0 else (
                2.0 if amount > 0 else 0.0
    )
    balance_utilisation_pct = float(amount / account_balance * 100) if account_balance and account_balance > 0 else 100.0

    return FeatureSet(
        amount=amount,
        avg_amount=avg_amount,
        max_amount=max_amount,
        is_new_recipient=is_new_recipient,
        is_new_device=is_new_device,
        is_unusual_city=is_unusual_city,
        is_unusual_country=is_unusual_country,
        is_unusual_time=is_unusual_time,
        hour_of_day=now_hour,
        txns_last_24h=txns_last_24h,
        txns_in_velocity_window=txns_in_velocity_window,
        amount_ratio_to_avg=amount_ratio_to_avg,
        balance_utilisation_pct=balance_utilisation_pct,
        acknowledged_beneficiary_warning=acknowledged_beneficiary_warning,
        median_amount=median_amount,
        history_count=history_count,
    )


# ---------------------------------------------------------------------
# Layer 1: Customer Behaviour Analysis
# ---------------------------------------------------------------------
def behaviour_tier(features: FeatureSet) -> str:
    has_history = features.avg_amount > 0 or features.history_count > 0
    if not has_history:
        # A brand-new user has no baseline to compare against yet -- judge
        # only on absolute amount, conservatively.
        if features.amount >= Decimal("500000"):
            return "HIGH_CONCERN"
        if features.amount >= Decimal("200000"):
            return "MEDIUM_CONCERN"
        return "NORMAL"

    ratio = features.amount_ratio_to_avg
    exceeds_historical_max = features.max_amount > 0 and features.amount > features.max_amount * Decimal("1.5")

    if ratio >= 8 or exceeds_historical_max:
        return "HIGH_CONCERN"
    if ratio >= 4:
        return "MEDIUM_CONCERN"
    if ratio >= 2:
        return "LOW_CONCERN"
    return "NORMAL"


# ---------------------------------------------------------------------
# Layer 2: Device & Location Analysis
# ---------------------------------------------------------------------
def device_location_tier(features: FeatureSet) -> str:
    unusual_location = features.is_unusual_city or features.is_unusual_country

    if features.is_new_device and unusual_location:
        return "SUSPICIOUS"
    if features.is_new_device or unusual_location:
        return "REQUIRES_ATTENTION"
    return "TRUSTED"


# ---------------------------------------------------------------------
# Layer 3: Transaction Context Analysis
# ---------------------------------------------------------------------
def transaction_context_flags(features: FeatureSet) -> List[str]:
    flags: List[str] = []

    if features.txns_in_velocity_window >= VELOCITY_TRANSACTION_THRESHOLD:
        flags.append("HIGH_VELOCITY")

    if features.is_new_recipient and features.amount_ratio_to_avg >= 4:
        flags.append("NEW_BENEFICIARY_LARGE_AMOUNT")

    if features.is_unusual_time:
        flags.append("UNUSUAL_TIME")

    if features.balance_utilisation_pct >= 90:
        flags.append("SPENDING_SPIKE")

    if features.acknowledged_beneficiary_warning:
        flags.append("PROCEEDED_PAST_BENEFICIARY_WARNING")

    return flags


# ---------------------------------------------------------------------
# Layer 4: Beneficiary Risk Analysis
# ---------------------------------------------------------------------
def beneficiary_tier(db: Session, recipient_account_number: str) -> tuple[str, Optional[str]]:
    """Returns (tier, reason). No stored row = UNKNOWN (the default)."""
    profile = (
        db.query(BeneficiaryRiskProfile)
        .filter(BeneficiaryRiskProfile.account_number == recipient_account_number)
        .first()
    )
    if not profile:
        return "UNKNOWN", None
    return profile.risk_category.value, profile.reason


# ---------------------------------------------------------------------
# Fraud Decision Engine -- the rule table. Read top to bottom, first
# match wins. Nothing here is a sum; every rule is a plain condition.
# ---------------------------------------------------------------------
def decide(layers: LayerResults) -> RiskAssessment:
    reasons: List[str] = []

    other_layers_concerned = 0
    if layers.device_location_tier == "SUSPICIOUS":
        other_layers_concerned += 1
    if layers.behaviour_tier == "HIGH_CONCERN":
        other_layers_concerned += 1
    if layers.context_flags:
        other_layers_concerned += 1

    # Rule 1: high-risk beneficiary + multiple other concerns -> CRITICAL
    if layers.beneficiary_tier == "HIGH_RISK" and other_layers_concerned >= CONCERN_ESCALATION_COUNT:
        reasons.append(f"Recipient account is on the fraud watchlist as HIGH_RISK{': ' + layers.beneficiary_reason if layers.beneficiary_reason else ''}")
        reasons.append("Multiple additional risk indicators were present simultaneously")
        _append_layer_reasons(reasons, layers)
        return RiskAssessment(level=RiskLevel.critical, reasons=reasons, layers=layers)

    # Rule 2: high-risk beneficiary alone -> HIGH_RISK
    if layers.beneficiary_tier == "HIGH_RISK":
        reasons.append(f"Recipient account is on the fraud watchlist as HIGH_RISK{': ' + layers.beneficiary_reason if layers.beneficiary_reason else ''}")
        return RiskAssessment(level=RiskLevel.high_risk, reasons=reasons, layers=layers)

    # Rule 3: watchlisted beneficiary + another concern -> HIGH_RISK
    if layers.beneficiary_tier == "WATCHLISTED" and other_layers_concerned >= 1:
        reasons.append(f"Recipient account is watchlisted{': ' + layers.beneficiary_reason if layers.beneficiary_reason else ''}")
        _append_layer_reasons(reasons, layers)
        return RiskAssessment(level=RiskLevel.high_risk, reasons=reasons, layers=layers)

    # Rule 4: watchlisted beneficiary alone -> VERIFY
    if layers.beneficiary_tier == "WATCHLISTED":
        reasons.append(f"Recipient account is watchlisted{': ' + layers.beneficiary_reason if layers.beneficiary_reason else ''}")
        return RiskAssessment(level=RiskLevel.verify, reasons=reasons, layers=layers)

    # Rule 5: suspicious device/location AND high behavioural concern -> HIGH_RISK
    if layers.device_location_tier == "SUSPICIOUS" and layers.behaviour_tier == "HIGH_CONCERN":
        reasons.append("Transaction from an unrecognised device in an unfamiliar location")
        reasons.append("Transaction amount is far above this user's normal range")
        return RiskAssessment(level=RiskLevel.high_risk, reasons=reasons, layers=layers)
    # Rule 5b: far-above-normal amount plus any other concern -> HIGH_RISK
    if layers.behaviour_tier == "HIGH_CONCERN" and (
        layers.device_location_tier == "REQUIRES_ATTENTION"
        or "NEW_BENEFICIARY_LARGE_AMOUNT" in layers.context_flags
        or "UNUSUAL_TIME" in layers.context_flags
    ):
        reasons.append("Transaction amount is far above this user's normal range")
        _append_layer_reasons(reasons, layers)
        return RiskAssessment(level=RiskLevel.high_risk, reasons=reasons, layers=layers)
    # Rule 6: any single severe signal -> VERIFY
    if layers.device_location_tier == "SUSPICIOUS":
        reasons.append("Transaction from an unrecognised device in an unfamiliar location")
        return RiskAssessment(level=RiskLevel.verify, reasons=reasons, layers=layers)
    if layers.behaviour_tier == "HIGH_CONCERN":
        reasons.append("Transaction amount is far above this user's normal range")
        return RiskAssessment(level=RiskLevel.verify, reasons=reasons, layers=layers)
    if "HIGH_VELOCITY" in layers.context_flags:
        reasons.append("Abnormally high number of transactions in a short time window")
        return RiskAssessment(level=RiskLevel.verify, reasons=reasons, layers=layers)
    if "NEW_BENEFICIARY_LARGE_AMOUNT" in layers.context_flags:
        reasons.append("Large transaction to a recipient this user has never paid before")
        return RiskAssessment(level=RiskLevel.verify, reasons=reasons, layers=layers)

    # Rule 7: any mild concern at all -> CAUTION
    mild_concern = (
        layers.behaviour_tier == "LOW_CONCERN"
        or layers.behaviour_tier == "MEDIUM_CONCERN"
        or layers.device_location_tier == "REQUIRES_ATTENTION"
        or layers.beneficiary_tier == "UNKNOWN"
        or bool(layers.context_flags)
    )
    if mild_concern:
        if layers.behaviour_tier in ("LOW_CONCERN", "MEDIUM_CONCERN"):
            reasons.append("Transaction amount is somewhat above this user's normal range")
        if layers.device_location_tier == "REQUIRES_ATTENTION":
            reasons.append("Transaction from a new device or an unfamiliar location")
        if layers.beneficiary_tier == "UNKNOWN":
            reasons.append("First transaction to this recipient")
        _append_layer_reasons(reasons, layers, skip_duplicates=True)
        return RiskAssessment(level=RiskLevel.caution, reasons=reasons, layers=layers)

    # Rule 8: nothing raised any concern -> SAFE
    reasons.append("No anomalies detected -- transaction matches this user's established behaviour")
    return RiskAssessment(level=RiskLevel.safe, reasons=reasons, layers=layers)


def _append_layer_reasons(reasons: List[str], layers: LayerResults, skip_duplicates: bool = False) -> None:
    """Adds human-readable context-flag explanations without repeating ones already added."""
    flag_text = {
        "HIGH_VELOCITY": "Abnormally high number of transactions in a short time window",
        "NEW_BENEFICIARY_LARGE_AMOUNT": "Large transaction to a recipient this user has never paid before",
        "UNUSUAL_TIME": "Transaction occurred at an unusual time for this user",
        "SPENDING_SPIKE": "Transaction consumes nearly all of the account balance",
        "PROCEEDED_PAST_BENEFICIARY_WARNING": "Customer proceeded despite a recipient risk warning",
    }
    for flag in layers.context_flags:
        text = flag_text.get(flag)
        if text and (not skip_duplicates or text not in reasons):
            reasons.append(text)
