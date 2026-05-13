from enum import StrEnum

from pydantic import BaseModel


class AuditAction(StrEnum):
    create = "create"
    update = "update"
    delete = "delete"
    restore = "restore"
    deposit = "deposit"
    transfer = "transfer"


class AuditEntry(BaseModel):
    id: str
    action: AuditAction
    entity_type: str
    entity_id: str
    actor_id: str
    actor_type: str
    timestamp: str
    details: dict | None = None
