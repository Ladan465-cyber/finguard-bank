from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_event(
    db: Session,
    actor_type: str,
    action: str,
    actor_id: str = None,
    entity_type: str = None,
    entity_id: str = None,
    details: dict = None,
    ip_address: str = None,
):
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
