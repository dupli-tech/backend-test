import uuid
from datetime import UTC, datetime

from app.audit_models import AuditAction, AuditEntry

_audit_db: list[AuditEntry] = []


def record_audit(
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    actor_id: str,
    actor_type: str,
    details: dict | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        id=str(uuid.uuid4()),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        actor_type=actor_type,
        timestamp=datetime.now(UTC).isoformat(),
        details=details,
    )
    _audit_db.append(entry)
    return entry


def list_audit(
    offset: int = 0,
    limit: int = 20,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
) -> tuple[list[AuditEntry], int]:
    filtered = list(_audit_db)
    if entity_type:
        filtered = [e for e in filtered if e.entity_type == entity_type]
    if entity_id:
        filtered = [e for e in filtered if e.entity_id == entity_id]
    if actor_id:
        filtered = [e for e in filtered if e.actor_id == actor_id]
    total = len(filtered)
    return filtered[offset : offset + limit], total
