"""Departments & positions (Module 3)."""
from sqlalchemy.orm import Session

from ..core.errors import BadRequest, Conflict, NotFound
from ..models import Department, Position, User
from ..repositories import audit_repo, department_repo, employee_repo
from ..serializers import department_out, position_out


def list_departments(db: Session) -> list[dict]:
    return [department_out(d) for d in department_repo.list_all(db)]


def create_department(db: Session, actor: User, data: dict) -> dict:
    if department_repo.get_by_name(db, data["name"]):
        raise Conflict("A department with this name already exists")
    dept = department_repo.add(db, Department(**data))
    dept.code = f"DIVISION-{dept.id:02d}"
    audit_repo.add(db, actor.username, "CREATE", f"Department '{dept.name}'")
    db.commit()
    db.refresh(dept)
    return department_out(dept)


def update_department(db: Session, actor: User, department_id: int, changes: dict) -> dict:
    dept = department_repo.get(db, department_id)
    if dept is None:
        raise NotFound("Department not found")
    for key, value in changes.items():
        setattr(dept, key, value)
    audit_repo.add(db, actor.username, "UPDATE", f"Department '{dept.name}'")
    db.commit()
    db.refresh(dept)
    return department_out(dept)


def list_positions(db: Session, department_id: int | None) -> list[dict]:
    counts = employee_repo.headcount_by_position(db)
    return [position_out(p, counts.get((p.department_id, p.title), 0))
            for p in department_repo.list_positions(db, department_id)]


def _get_position(db: Session, position_id: int) -> Position:
    pos = department_repo.get_position(db, position_id)
    if pos is None:
        raise NotFound("Job role not found")
    return pos


def _headcount(db: Session, pos: Position) -> int:
    return employee_repo.headcount_by_position(db).get((pos.department_id, pos.title), 0)


def create_position(db: Session, actor: User, data: dict) -> dict:
    if department_repo.get(db, data["department_id"]) is None:
        raise BadRequest("Unknown department")
    pos = department_repo.add_position(db, Position(**data))
    audit_repo.add(db, actor.username, "CREATE", f"Job role '{pos.title}'")
    db.commit()
    db.refresh(pos)
    return position_out(pos, 0)


def update_position(db: Session, actor: User, position_id: int, data: dict) -> dict:
    pos = _get_position(db, position_id)
    old_title, old_dept = pos.title, pos.department_id
    for key, value in data.items():
        setattr(pos, key, value)
    if pos.title != old_title:  # keep assigned employees in sync with the renamed role
        employee_repo.rename_position(db, old_dept, old_title, pos.title)
    audit_repo.add(db, actor.username, "UPDATE", f"Job role '{pos.title}'")
    db.commit()
    return position_out(pos, _headcount(db, pos))


def delete_position(db: Session, actor: User, position_id: int) -> None:
    pos = _get_position(db, position_id)
    if _headcount(db, pos):
        raise Conflict("Reassign the employees in this role before deleting it")
    audit_repo.add(db, actor.username, "DELETE", f"Job role '{pos.title}'")
    department_repo.delete_position(db, pos)
    db.commit()
