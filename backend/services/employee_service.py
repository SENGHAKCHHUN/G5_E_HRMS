"""Employee management (Module 2)."""
from sqlalchemy.orm import Session

from ..core import security
from ..core.errors import BadRequest, Conflict, Forbidden, NotFound
from ..core.pagination import ALL, Page
from ..models import Employee, User
from ..repositories import audit_repo, department_repo, employee_repo, user_repo
from ..repositories.paging import paginate
from ..serializers import employee_out
from .access import ensure_self_or_staff, is_staff


def _get(db: Session, employee_id: int) -> Employee:
    emp = employee_repo.get(db, employee_id)
    if emp is None:
        raise NotFound("Employee not found")
    return emp


def _ensure_unique_email(db: Session, email: str, exclude_id: int | None = None):
    if employee_repo.get_by_email(db, email, exclude_id):
        raise Conflict("Another employee already uses this email")


def _ensure_department(db: Session, department_id: int):
    if department_repo.get(db, department_id) is None:
        raise BadRequest("Unknown department")


def list_for(db: Session, user: User, page: Page = ALL, search: str | None = None,
             department_id: int | None = None, position: str | None = None,
             status: str | None = None) -> tuple[list[dict], int]:
    """Staff see everyone (with optional filters); employees only their own profile."""
    only = None if is_staff(user) else user.employee_id
    stmt = employee_repo.employees_query(only, search, department_id, position, status)
    rows, total = paginate(db, stmt, page)
    return [employee_out(e) for e in rows], total


def summary(db: Session) -> dict:
    """Head-count per status for the directory's summary cards."""
    by_status = employee_repo.count_by_status(db)
    return {"total": sum(by_status.values()), "by_status": by_status}


def get_for(db: Session, user: User, employee_id: int) -> dict:
    ensure_self_or_staff(user, employee_id)
    return employee_out(_get(db, employee_id))


def create(db: Session, actor: User, data: dict) -> dict:
    """Creates the employee and their login (username = email before '@', one-time password)."""
    role = data.pop("role", security.EMPLOYEE)
    _ensure_department(db, data["department_id"])
    if role == security.ADMIN and actor.role != security.ADMIN:
        raise Forbidden("Only an Admin can create Admin accounts")
    data["email"] = data["email"].lower()
    _ensure_unique_email(db, data["email"])
    emp = employee_repo.add(db, Employee(**data))

    username = emp.email.split("@")[0]
    if user_repo.get_by_username(db, username):
        username = f"{username}{emp.id}"
    initial_password = security.temporary_password()  # must be changed at first login
    user_repo.add(db, User(username=username, password_hash=security.hash_password(initial_password),
                           role=role, employee_id=emp.id, must_change_password=True))
    audit_repo.add(db, actor.username, "CREATE", f"Employee {emp.code} {emp.full_name} (login '{username}')")
    db.commit()
    db.refresh(emp)
    return {**employee_out(emp), "username": username, "initial_password": initial_password}


def update(db: Session, actor: User, employee_id: int, changes: dict) -> dict:
    emp = _get(db, employee_id)
    role = changes.pop("role", None)
    if "email" in changes:
        changes["email"] = changes["email"].lower()
        _ensure_unique_email(db, changes["email"], exclude_id=employee_id)
    if "department_id" in changes:
        _ensure_department(db, changes["department_id"])
    for key, value in changes.items():
        setattr(emp, key, value)
    if role and emp.user and role != emp.user.role:
        if actor.role != security.ADMIN:
            raise Forbidden("Only an Admin can change system roles")
        emp.user.role = role
    audit_repo.add(db, actor.username, "UPDATE", f"Employee {emp.code} updated")
    db.commit()
    db.refresh(emp)
    return employee_out(emp)


def delete(db: Session, actor: User, employee_id: int) -> None:
    emp = _get(db, employee_id)
    if emp.id == actor.employee_id:
        raise BadRequest("You cannot delete your own record")
    audit_repo.add(db, actor.username, "DELETE", f"Employee {emp.code} {emp.full_name} removed")
    employee_repo.delete(db, emp)
    db.commit()
