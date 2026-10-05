import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account import Account
from app.models.device import Device
from app.models.behavior import UserBehaviorProfile
from app.models.transaction import Transaction, TransactionStatus, RiskLevel, TransactionType
from app.models.fraud import FraudEvent, VerificationAttempt, VerificationMethod, VerificationResult
from app.services import fraud_engine, behavior_service, otp_service, audit_service, face_service
from app.schemas.transaction_schemas import TransactionCreate

MAX_OTP_ATTEMPTS = 3
MAX_FACE_ATTEMPTS = 3

CUSTOMER_MESSAGES = {
    RiskLevel.safe: "Transaction successful.",
    RiskLevel.caution: "Transaction successful. Please note: this transfer had one or more unusual characteristics, so keep an eye on your recent activity.",
    RiskLevel.verify: "Additional verification is required to complete this transaction.",
    RiskLevel.high_risk: "For your security, this transaction requires OTP verification followed by identity verification.",
    RiskLevel.critical: "Transaction completed. It was flagged as high-risk and has been logged for review.",
}


def _gen_reference() -> str:
    return "FGX" + "".join(random.choices(string.digits, k=10))


def register_or_touch_device(db: Session, user_id: str, fingerprint: str, browser: str, os_: str) -> Device:
    device = db.query(Device).filter(
        Device.user_id == user_id, Device.device_fingerprint == fingerprint
    ).first()
    if device:
        device.last_seen_at = datetime.utcnow()
        device.times_used = (device.times_used or 0) + 1
        # a device becomes "trusted" after being used successfully more than once
        if device.times_used >= 2:
            device.is_trusted = True
        db.commit()
        return device

    device = Device(
        user_id=user_id,
        device_fingerprint=fingerprint,
        browser=browser,
        operating_system=os_,
        is_trusted=False,
        times_used=1,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def assess_transaction(db: Session, user, payload: TransactionCreate):
    """Runs the fraud engine only. Writes nothing, so it's safe for previews."""
    account: Account = db.query(Account).filter(Account.user_id == user.id).first()
    if not account:
        raise ValueError("Sender account not found")

    if payload.recipient_account_number == account.account_number:
        raise ValueError("You cannot transfer to your own account.")

    recipient = db.query(Account).filter(
        Account.account_number == payload.recipient_account_number
    ).first()
    if not recipient:
        raise ValueError("Account does not exist. Please check the account number and try again.")

    if payload.amount > account.balance:
        raise ValueError("Insufficient balance")

    is_known_device_before = db.query(Device).filter(
        Device.user_id == user.id,
        Device.device_fingerprint == payload.device_fingerprint,
        Device.is_trusted == True,  # noqa: E712
    ).first() is not None

    profile = db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user.id).first()
    txns_24h = behavior_service.get_txns_last_24h(db, user.id)
    txns_velocity = behavior_service.get_txns_in_velocity_window(db, user.id, fraud_engine.VELOCITY_WINDOW_MINUTES)

    features = fraud_engine.extract_features(
        db=db, profile=profile, amount=payload.amount,
        recipient_account_number=payload.recipient_account_number,
        device_fingerprint=payload.device_fingerprint,
        city=payload.city, country=payload.country, user_id=user.id,
        account_balance=account.balance, simulated_hour=payload.simulated_hour,
        txns_last_24h=txns_24h, txns_in_velocity_window=txns_velocity,
        acknowledged_beneficiary_warning=payload.acknowledged_beneficiary_warning,
    )
    features.is_new_device = not is_known_device_before

    beneficiary_category, beneficiary_reason = fraud_engine.beneficiary_tier(db, payload.recipient_account_number)
    layers = fraud_engine.LayerResults(
        behaviour_tier=fraud_engine.behaviour_tier(features),
        device_location_tier=fraud_engine.device_location_tier(features),
        context_flags=fraud_engine.transaction_context_flags(features),
        beneficiary_tier=beneficiary_category,
        beneficiary_reason=beneficiary_reason,
    )
    return account, fraud_engine.decide(layers)


def create_and_assess_transaction(db: Session, user, payload: TransactionCreate) -> dict:
    account, assessment = assess_transaction(db, user, payload)

    # Register device usage (after scoring, so scoring reflects state BEFORE this attempt)
    register_or_touch_device(db, user.id, payload.device_fingerprint, payload.browser, payload.operating_system)

    reference = _gen_reference()
    txn = Transaction(
        reference=reference,
        sender_id=user.id,
        sender_account_number=account.account_number,
        recipient_account_number=payload.recipient_account_number,
        recipient_name=payload.recipient_name,
        recipient_bank=payload.recipient_bank,
        amount=payload.amount,
        transaction_type=TransactionType(payload.transaction_type),
        narration=payload.narration,
        device_fingerprint=payload.device_fingerprint,
        browser=payload.browser,
        operating_system=payload.operating_system,
        ip_address=payload.ip_address,
        city=payload.city,
        country=payload.country,
        risk_level=assessment.level,
        risk_score=None,
        risk_factors=assessment.reasons,
        fraud_rule_version=assessment.rule_version,
        status=TransactionStatus.pending,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    result = {
        "transaction_id": txn.id,
        "reference": txn.reference,
        "risk_level": assessment.level.value,
        "customer_message": CUSTOMER_MESSAGES[assessment.level],
        "requires_otp": False,
        "requires_verification": False,
    }

    if assessment.level in (RiskLevel.safe, RiskLevel.caution):
        _complete_transaction(db, txn, account)
        result["status"] = TransactionStatus.completed.value

    elif assessment.level == RiskLevel.verify:
        txn.status = TransactionStatus.awaiting_otp
        db.commit()
        _create_fraud_event(db, txn, assessment)
        result["status"] = TransactionStatus.awaiting_otp.value
        result.update(_issue_otp(db, txn, user))

    elif assessment.level == RiskLevel.high_risk:
        # HIGH_RISK requires OTP *then* facial verification -- OTP first.
        # confirm_otp() checks txn.risk_level == HIGH_RISK afterwards and
        # chains into facial verification instead of completing.
        txn.status = TransactionStatus.awaiting_otp
        db.commit()
        _create_fraud_event(db, txn, assessment)
        result["status"] = TransactionStatus.awaiting_otp.value
        result.update(_issue_otp(db, txn, user))

    else:  # CRITICAL: no longer blocked. The customer was warned and chose to proceed.
        _create_fraud_event(db, txn, assessment)
        audit_service.log_event(
            db, actor_type="system", action="TRANSACTION_FLAGGED_CRITICAL",
            entity_type="transaction", entity_id=txn.id,
            details={"reasons": assessment.reasons},
        )
        _complete_transaction(db, txn, account)
        result["status"] = TransactionStatus.completed.value

    return result


def _issue_otp(db: Session, txn: Transaction, user) -> dict:
    code = otp_service.generate_otp()
    va = VerificationAttempt(
        transaction_id=txn.id,
        method=VerificationMethod.otp,
        code_hash=otp_service.hash_otp(code),
        expires_at=otp_service.otp_expiry(),
    )
    db.add(va)
    db.commit()
    demo_code = otp_service.demo_deliver(code, user.phone)
    extra = {"requires_otp": True}
    if demo_code:
        extra["demo_otp_code"] = demo_code  # ONLY populated in OTP_DEMO_MODE
    return extra


def _create_fraud_event(db: Session, txn: Transaction, assessment) -> FraudEvent:
    event = FraudEvent(
        transaction_id=txn.id,
        user_id=txn.sender_id,
        risk_level=assessment.level.value,
        risk_score=None,
        risk_factors=assessment.reasons,
        fraud_rule_version=assessment.rule_version,
    )
    db.add(event)
    db.commit()
    return event


def _complete_transaction(db: Session, txn: Transaction, sender_account: Account):
    sender_account.balance = Decimal(sender_account.balance) - Decimal(txn.amount)
    recipient_account = db.query(Account).filter(
        Account.account_number == txn.recipient_account_number
    ).first()
    if recipient_account:
        recipient_account.balance = Decimal(recipient_account.balance) + Decimal(txn.amount)

    txn.status = TransactionStatus.completed
    txn.completed_at = datetime.utcnow()
    db.commit()

    behavior_service.refresh_behavior_profile(db, txn.sender_id)
    audit_service.log_event(
        db, actor_type="system", action="TRANSACTION_COMPLETED",
        entity_type="transaction", entity_id=txn.id,
        details={"amount": str(txn.amount), "risk_level": txn.risk_level.value if txn.risk_level else None},
    )


def confirm_otp(db: Session, user, transaction_id: str, otp_code: str) -> dict:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.sender_id == user.id).first()
    if not txn:
        raise ValueError("Transaction not found")
    if txn.status != TransactionStatus.awaiting_otp:
        raise ValueError("Transaction is not awaiting OTP verification")

    va = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.transaction_id == txn.id, VerificationAttempt.method == VerificationMethod.otp)
        .order_by(VerificationAttempt.created_at.desc())
        .first()
    )
    if not va:
        raise ValueError("No OTP challenge found for this transaction")

    if va.expires_at and datetime.utcnow() > va.expires_at:
        va.result = VerificationResult.expired
        db.commit()
        raise ValueError("OTP has expired. Please retry the transaction.")

    if not otp_service.verify_otp(otp_code, va.code_hash):
        attempts = int(va.attempts_made or "0") + 1
        va.attempts_made = str(attempts)
        audit_service.log_event(
            db, actor_type="user", actor_id=user.id, action="OTP_FAILED",
            entity_type="transaction", entity_id=txn.id,
        )
        if attempts >= MAX_OTP_ATTEMPTS:
            va.result = VerificationResult.failed
            txn.status = TransactionStatus.rejected
            db.commit()
            return {"success": False, "status": txn.status.value,
                    "message": "Incorrect OTP. Too many attempts, so this transaction was rejected."}
        db.commit()
        left = MAX_OTP_ATTEMPTS - attempts
        return {"success": False, "status": txn.status.value,
                "message": f"Incorrect OTP. You have {left} attempt{'s' if left != 1 else ''} left."}

    va.result = VerificationResult.success
    va.verified_at = datetime.utcnow()
    db.commit()
    audit_service.log_event(
        db, actor_type="user", actor_id=user.id, action="OTP_VERIFIED",
        entity_type="transaction", entity_id=txn.id,
    )

    # HIGH_RISK chains into facial verification instead of completing here.
    if txn.risk_level == RiskLevel.high_risk:
        txn.status = TransactionStatus.awaiting_verification
        db.commit()
        va_face = VerificationAttempt(
            transaction_id=txn.id,
            method=VerificationMethod.facial_simulation,
            expires_at=otp_service.otp_expiry(),
        )
        db.add(va_face)
        db.commit()
        return {
            "success": True,
            "status": txn.status.value,
            "requires_further_verification": True,
            "transaction_id": txn.id,
            "reference": txn.reference,
            "message": "OTP verified. Additional identity verification is required to complete this transaction.",
        }

    account = db.query(Account).filter(Account.user_id == user.id).first()
    _complete_transaction(db, txn, account)
    return {"success": True, "status": txn.status.value, "message": "Transaction successful."}


def confirm_facial_verification(db: Session, user, transaction_id: str, live_descriptor: list) -> dict:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.sender_id == user.id).first()
    if not txn:
        raise ValueError("Transaction not found")
    if txn.status != TransactionStatus.awaiting_verification:
        raise ValueError("Transaction is not awaiting identity verification")

    # Lock out after 3 failed face checks in 15 minutes
    recent_failures = (
        db.query(VerificationAttempt)
        .join(Transaction, Transaction.id == VerificationAttempt.transaction_id)
        .filter(
            Transaction.sender_id == user.id,
            VerificationAttempt.method == VerificationMethod.facial_simulation,
            VerificationAttempt.result == VerificationResult.failed,
            VerificationAttempt.created_at > datetime.utcnow() - timedelta(minutes=15),
        )
        .count()
    )
    if recent_failures >= 3:
        txn.status = TransactionStatus.rejected
        db.commit()
        raise ValueError("Too many failed identity checks. Please try again in 15 minutes.")

    va = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.transaction_id == txn.id, VerificationAttempt.method == VerificationMethod.facial_simulation)
        .order_by(VerificationAttempt.created_at.desc())
        .first()
    )

    if not user.face_descriptor:
        raise ValueError(
            "No enrolled Face ID found for this account. Please enroll your face "
            "on the Security page before attempting this verification."
        )

    matched, distance = face_service.is_match(user.face_descriptor, live_descriptor)
    print("FACE DISTANCE:", distance, "| matched:", matched)

    if not matched:
        attempts = int(va.attempts_made or "0") + 1 if va else 1
        if va:
            va.attempts_made = str(attempts)
        audit_service.log_event(
            db, actor_type="user", actor_id=user.id, action="FACIAL_VERIFICATION_FAILED",
            entity_type="transaction", entity_id=txn.id, details={"distance": distance},
        )
        if attempts >= MAX_FACE_ATTEMPTS:
            if va:
                va.result = VerificationResult.failed
            txn.status = TransactionStatus.rejected
            db.commit()
            return {"success": False, "status": txn.status.value,
                    "message": "Face did not match. Too many attempts, so this transaction was rejected."}
        db.commit()
        left = MAX_FACE_ATTEMPTS - attempts
        return {"success": False, "status": txn.status.value,
                "message": f"Face did not match. You have {left} attempt{'s' if left != 1 else ''} left."}

    if va:
        va.result = VerificationResult.success
        va.verified_at = datetime.utcnow()
        db.commit()

    account = db.query(Account).filter(Account.user_id == user.id).first()
    _complete_transaction(db, txn, account)
    audit_service.log_event(
        db, actor_type="user", actor_id=user.id, action="FACIAL_VERIFICATION_SUCCESS",
        entity_type="transaction", entity_id=txn.id, details={"distance": distance},
    )
    return {"success": True, "status": txn.status.value, "message": "Transaction successful."}