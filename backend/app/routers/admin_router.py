from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.models.user import User, AdminUser
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.models.fraud import FraudEvent, FraudEventStatus
from app.models.audit import AuditLog
from app.models.device import Device

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard/stats")
def dashboard_stats(current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    total = db.query(func.count(Transaction.id)).scalar() or 0
    completed = db.query(func.count(Transaction.id)).filter(Transaction.status == TransactionStatus.completed).scalar() or 0
    blocked = db.query(func.count(Transaction.id)).filter(Transaction.status == TransactionStatus.blocked).scalar() or 0
    awaiting_otp = db.query(func.count(Transaction.id)).filter(Transaction.status == TransactionStatus.awaiting_otp).scalar() or 0
    awaiting_verification = db.query(func.count(Transaction.id)).filter(Transaction.status == TransactionStatus.awaiting_verification).scalar() or 0
    high_risk = db.query(func.count(Transaction.id)).filter(Transaction.risk_level == RiskLevel.high).scalar() or 0
    critical_risk = db.query(func.count(Transaction.id)).filter(Transaction.risk_level == RiskLevel.critical).scalar() or 0
    open_alerts = db.query(func.count(FraudEvent.id)).filter(FraudEvent.status == FraudEventStatus.open).scalar() or 0

    total_volume = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.status == TransactionStatus.completed
    ).scalar() or 0

    since_24h = datetime.utcnow() - timedelta(hours=24)
    txns_24h = db.query(func.count(Transaction.id)).filter(Transaction.created_at >= since_24h).scalar() or 0

    return {
        "total_transactions": total,
        "successful_transactions": completed,
        "blocked_transactions": blocked,
        "transactions_requiring_verification": awaiting_otp + awaiting_verification,
        "open_fraud_alerts": open_alerts,
        "high_risk_transactions": high_risk,
        "critical_risk_transactions": critical_risk,
        "total_completed_volume_ngn": str(total_volume),
        "transactions_last_24h": txns_24h,
    }


@router.get("/transactions")
def monitor_transactions(
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).join(User, Transaction.sender_id == User.id)
    if risk_level:
        q = q.filter(Transaction.risk_level == risk_level.upper())
    if status:
        q = q.filter(Transaction.status == status)
    rows = q.order_by(Transaction.created_at.desc()).limit(limit).all()

    out = []
    for t in rows:
        out.append({
            "id": t.id,
            "reference": t.reference,
            "user_name": t.sender.full_name if t.sender else "Unknown",
            "user_email": t.sender.email if t.sender else None,
            "amount": str(t.amount),
            "recipient_account_number": t.recipient_account_number,
            "recipient_name": t.recipient_name,
            "created_at": t.created_at,
            "device_fingerprint": t.device_fingerprint,
            "browser": t.browser,
            "operating_system": t.operating_system,
            "city": t.city,
            "country": t.country,
            "risk_level": t.risk_level.value if t.risk_level else None,
            "risk_score": str(t.risk_score) if t.risk_score is not None else None,
            "risk_factors": t.risk_factors,
            "status": t.status.value,
            "investigation_status": t.investigation_status.value if t.investigation_status else "none",
        })
    return out


@router.get("/transactions/{transaction_id}")
def transaction_detail(transaction_id: str, current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(404, "Transaction not found")
    return {
        "id": t.id,
        "reference": t.reference,
        "user": {
            "id": t.sender.id, "full_name": t.sender.full_name, "email": t.sender.email, "phone": t.sender.phone,
        } if t.sender else None,
        "amount": str(t.amount),
        "transaction_type": t.transaction_type.value,
        "recipient_account_number": t.recipient_account_number,
        "recipient_name": t.recipient_name,
        "recipient_bank": t.recipient_bank,
        "narration": t.narration,
        "device_fingerprint": t.device_fingerprint,
        "browser": t.browser,
        "operating_system": t.operating_system,
        "ip_address": t.ip_address,
        "city": t.city,
        "country": t.country,
        "risk_level": t.risk_level.value if t.risk_level else None,
        "risk_score": str(t.risk_score) if t.risk_score is not None else None,
        "risk_factors": t.risk_factors,
        "fraud_rule_version": t.fraud_rule_version,
        "status": t.status.value,
        "investigation_status": t.investigation_status.value if t.investigation_status else "none",
        "created_at": t.created_at,
        "completed_at": t.completed_at,
    }


@router.get("/fraud-alerts")
def fraud_alerts(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(FraudEvent)
    if status:
        q = q.filter(FraudEvent.status == status)
    rows = q.order_by(FraudEvent.created_at.desc()).limit(limit).all()
    out = []
    for e in rows:
        txn = e.transaction
        out.append({
            "id": e.id,
            "transaction_id": e.transaction_id,
            "transaction_reference": txn.reference if txn else None,
            "user_name": txn.sender.full_name if txn and txn.sender else None,
            "amount": str(txn.amount) if txn else None,
            "risk_level": e.risk_level,
            "risk_score": str(e.risk_score),
            "risk_factors": e.risk_factors,
            "status": e.status.value,
            "created_at": e.created_at,
        })
    return out


@router.post("/fraud-alerts/{event_id}/resolve")
def resolve_fraud_alert(
    event_id: str,
    resolution: str,  # 'resolved_fraud' | 'resolved_legitimate'
    notes: Optional[str] = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    event = db.query(FraudEvent).filter(FraudEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Fraud event not found")
    if resolution not in ("resolved_fraud", "resolved_legitimate"):
        raise HTTPException(400, "Invalid resolution value")

    event.status = resolution
    event.reviewed_by_admin_id = current_admin.id
    event.admin_notes = notes
    event.resolved_at = datetime.utcnow()

    if event.transaction:
        event.transaction.investigation_status = (
            "confirmed_fraud" if resolution == "resolved_fraud" else "confirmed_legitimate"
        )
    db.commit()
    return {"success": True}


@router.get("/audit-logs")
def audit_logs(limit: int = Query(200, le=1000), current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id, "actor_type": r.actor_type, "actor_id": r.actor_id, "action": r.action,
            "entity_type": r.entity_type, "entity_id": r.entity_id, "details": r.details,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/users")
def list_users(current_admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id, "full_name": u.full_name, "email": u.email, "phone": u.phone,
            "status": u.status.value, "home_city": u.home_city,
        }
        for u in users
    ]
