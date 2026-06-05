from sqlalchemy.orm import Session

from backend.app.models.entities import AuditLog


class AuditService:
    def log(self, db: Session, *, actor_id: str | None, entity_type: str, entity_id: str, action: str, payload: dict) -> None:
        db.add(
            AuditLog(
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload=payload,
            )
        )
