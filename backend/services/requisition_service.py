"""Job requisitions: requests to hire for a role (opened from Departments & Positions)."""
from sqlalchemy.orm import Session

from ..core.errors import BadRequest, Conflict, NotFound
from ..core.i18n import N_
from ..models import Requisition, User
from ..repositories import audit_repo, department_repo, requisition_repo
from ..serializers import requisition_out

ALREADY_CLOSED = {"Filled": N_("This requisition is already filled"),
                  "Cancelled": N_("This requisition is already cancelled"),
                  "other": N_("This requisition is closed")}


def list_requisitions(db: Session, department_id: int | None, status: str | None) -> list[dict]:
    return [requisition_out(r) for r in requisition_repo.list_all(db, department_id, status)]


def create(db: Session, actor: User, data: dict) -> dict:
    if department_repo.get(db, data["department_id"]) is None:
        raise BadRequest("Unknown department")
    if data.get("position_id") is not None:
        pos = department_repo.get_position(db, data["position_id"])
        if pos is None or pos.department_id != data["department_id"]:
            raise BadRequest("That job role does not belong to this department")
    req = requisition_repo.add(db, Requisition(**data, created_by=actor.username))
    audit_repo.add(db, actor.username, "REQUISITION", f"REQ-{req.id:04d}: {req.openings} x {req.title}")
    db.commit()
    db.refresh(req)
    return requisition_out(req)


def set_status(db: Session, actor: User, req_id: int, status: str) -> dict:
    req = requisition_repo.get(db, req_id)
    if req is None:
        raise NotFound("Requisition not found")
    if req.status != "Open":
        raise Conflict(ALREADY_CLOSED.get(req.status, ALREADY_CLOSED["other"]))
    req.status = status
    audit_repo.add(db, actor.username, "REQUISITION", f"REQ-{req.id:04d} marked {status.lower()}")
    db.commit()
    return requisition_out(req)
