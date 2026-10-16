"""Database access for employees."""
import re

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..models import Employee


def get(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def employees_query(only_id: int | None = None, search: str | None = None, department_id: int | None = None,
                    position: str | None = None, status: str | None = None) -> Select:
    stmt = select(Employee).options(joinedload(Employee.department), joinedload(Employee.user)).order_by(Employee.id)
    if only_id is not None:
        stmt = stmt.where(Employee.id == only_id)
    if search:
        stmt = stmt.where(search_condition(search))
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if position:
        stmt = stmt.where(Employee.position == position)
    if status:
        stmt = stmt.where(Employee.status == status)
    return stmt

def search_condition(search: str) -> ColumnElement[bool]:
    """Match an employee by name, email or code ('EMP-012' / '12')."""
    term = f"%{search.strip().lower()}%"
    conditions = [func.lower(Employee.first_name + " " + Employee.last_name).like(term),
                  func.lower(Employee.email).like(term)]
    digits = re.sub(r"^\s*emp-?0*", "", search.strip().lower())
    if digits.isdigit():
        conditions.append(Employee.id == int(digits))
    return or_(*conditions)



def list_all(db: Session, only_id: int | None = None) -> list[Employee]:
    return list(db.scalars(employees_query(only_id)).unique())


def get_by_email(db: Session, email: str, exclude_id: int | None = None) -> Employee | None:
    stmt = select(Employee).where(Employee.email == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(Employee.id != exclude_id)
    return db.scalars(stmt).first()


def count(db: Session, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Employee)
    if status:
        stmt = stmt.where(Employee.status == status)
    return db.scalar(stmt)


def count_by_status(db: Session) -> dict[str, int]:
    return dict(db.execute(select(Employee.status, func.count()).group_by(Employee.status)).all())


def add(db: Session, employee: Employee) -> Employee:
    db.add(employee)
    db.flush()  # assigns the id
    return employee


def delete(db: Session, employee: Employee) -> None:
    db.delete(employee)


def rename_position(db: Session, department_id: int, old_title: str, new_title: str) -> None:
    for emp in db.scalars(select(Employee).where(Employee.position == old_title,
                                                 Employee.department_id == department_id)):
        emp.position = new_title


def headcount_by_position(db: Session) -> dict[tuple[int, str], int]:
    rows = db.execute(select(Employee.department_id, Employee.position, func.count())
                      .group_by(Employee.department_id, Employee.position))
    return {(d, p): n for d, p, n in rows}
