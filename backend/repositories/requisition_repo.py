"""Database access for job requisitions."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Requisition


def get(db: Session, req_id: int) -> Requisition | None:
    return db.get(Requisition, req_id)


def list_all(db: Session, department_id: int | None = None, status: str | None = None) -> list[Requisition]:
    stmt = select(Requisition).order_by(Requisition.id.desc())
    if department_id:
        stmt = stmt.where(Requisition.department_id == department_id)
    if status:
        stmt = stmt.where(Requisition.status == status)
    return list(db.scalars(stmt))


def add(db: Session, req: Requisition) -> Requisition:
    db.add(req)
    db.flush()
    return req
