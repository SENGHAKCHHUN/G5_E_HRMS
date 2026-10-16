"""Database access for the audit log."""
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ..models import AuditLog


def add(db: Session, username: str, action: str, detail: str) -> None:
    db.add(AuditLog(username=username, action=action, detail=detail))


def recent_query() -> Select:
    return select(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
