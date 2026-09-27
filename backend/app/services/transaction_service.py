import random
import string
from datetime import datetime
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

CUSTOMER_MESSAGES = {
    RiskLevel.low: "Transaction successful.",
    RiskLevel.medium: "Additional verification is required to complete this transaction.",
    RiskLevel.high: "For your security, additional identity verification is required.",
    RiskLevel.critical: "Suspicious activity has been detected. This transaction cannot be completed at this time.",
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


def create_and_assess_transaction(db: Session, user, payload: TransactionCreate) -> dict:
    account: Account = db.query(Account).filter(Account.user_id == user.id).first()
    if not account:
        raise ValueError("Sender account not found")

    if payload.amount > account.balance:
        raise ValueError("Insufficient balance")

    # Register/observe the device used for this attempt BEFORE scoring,
    # but note: is_new_device in features is based on trust established
    # from PRIOR sessions, computed just before this call mutates it.
    is_known_device_before = db.query(Device).filter(
        Device.user_id == user.id,
        Device.device_fingerprint == payload.device_fingerprint,
        Device.is_trusted == True,  # noqa: E712
    ).first() is not None

    profile = db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user.id).first()
    txns_24h = behavior_service.get_txns_last_24h(db, user.id)

    features = fraud_engine.extract_features(
        db=db,
        profile=profile,
        amount=payload.amount,
        recipient_account_number=payload.recipient_account_number,
        device_fingerprint=payload.device_fingerprint,
        city=payload.city,
        country=payload.country,
        user_id=user.id,
        account_balance=account.balance,
        simulated_hour=payload.simulated_hour,
        txns_last_24h=txns_24h,
    )
    # Override the device-new determination with the pre-computed trust check
    features.is_new_device = not is_known_device_before

    assessment = fraud_engine.score_transaction(db, features, rule_version=settings.FRAUD_RULE_VERSION)

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
        risk_score=Decimal(str(assessment.score)),
        risk_factors=assessment.triggered_factors,
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

    if assessment.level == RiskLevel.low:
        _complete_transaction(db, txn, account)
        result["status"] = TransactionStatus.completed.value

    elif assessment.level == RiskLevel.medium:
        txn.status = TransactionStatus.awaiting_otp
        db.commit()
        _create_fraud_event(db, txn, assessment)
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
        result["status"] = TransactionStatus.awaiting_otp.value
        result["requires_otp"] = True
        if demo_code:
            result["demo_otp_code"] = demo_code  # ONLY populated in OTP_DEMO_MODE

    elif assessment.level == RiskLevel.high:
        txn.status = TransactionStatus.awaiting_verification
        db.commit()
        _create_fraud_event(db, txn, assessment)
        va = VerificationAttempt(
            transaction_id=txn.id,
            method=VerificationMethod.facial_simulation,
            expires_at=otp_service.otp_expiry(),
        )
        db.add(va)
        db.commit()
        result["status"] = TransactionStatus.awaiting_verification.value
        result["requires_verification"] = True

    else:  # CRITICAL
        txn.status = TransactionStatus.blocked
        txn.investigation_status = "open"
        db.commit()
        _create_fraud_event(db, txn, assessment)
        audit_service.log_event(
            db, actor_type="system", action="TRANSACTION_BLOCKED",
            entity_type="transaction", entity_id=txn.id,
            details={"risk_score": assessment.score, "factors": assessment.triggered_factors},
        )
        result["status"] = TransactionStatus.blocked.value

    return result


def _create_fraud_event(db: Session, txn: Transaction, assessment) -> FraudEvent:
    event = FraudEvent(
        transaction_id=txn.id,
        user_id=txn.sender_id,
        risk_level=assessment.level.value,
        risk_score=Decimal(str(assessment.score)),
        risk_factors=assessment.triggered_factors,
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
        va.result = VerificationResult.failed
        va.attempts_made = str(int(va.attempts_made or "0") + 1)
        db.commit()
        txn.status = TransactionStatus.rejected
        db.commit()
        audit_service.log_event(
            db, actor_type="user", actor_id=user.id, action="OTP_FAILED",
            entity_type="transaction", entity_id=txn.id,
        )
        return {"success": False, "status": txn.status.value, "message": "Incorrect OTP. Transaction rejected."}

    va.result = VerificationResult.success
    va.verified_at = datetime.utcnow()
    db.commit()

    account = db.query(Account).filter(Account.user_id == user.id).first()
    _complete_transaction(db, txn, account)
    audit_service.log_event(
        db, actor_type="user", actor_id=user.id, action="OTP_VERIFIED",
        entity_type="transaction", entity_id=txn.id,
    )
    return {"success": True, "status": txn.status.value, "message": "Transaction successful."}


def confirm_facial_verification(db: Session, user, transaction_id: str, live_descriptor: list) -> dict:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.sender_id == user.id).first()
    if not txn:
        raise ValueError("Transaction not found")
    if txn.status != TransactionStatus.awaiting_verification:
        raise ValueError("Transaction is not awaiting identity verification")

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

    if not matched:
        if va:
            va.result = VerificationResult.failed
            db.commit()
        txn.status = TransactionStatus.rejected
        db.commit()
        audit_service.log_event(
            db, actor_type="user", actor_id=user.id, action="FACIAL_VERIFICATION_FAILED",
            entity_type="transaction", entity_id=txn.id, details={"distance": distance},
        )
        return {"success": False, "status": txn.status.value, "message": "Face did not match. Transaction rejected."}

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