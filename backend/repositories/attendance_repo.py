"""Database access for attendance records."""
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Attendance, Employee
from .employee_repo import search_condition

_WITH_EMPLOYEE = joinedload(Attendance.employee).joinedload(Employee.department)


def get_for_day(db: Session, employee_id: int, day: date) -> Attendance | None:
    stmt = select(Attendance).where(Attendance.employee_id == employee_id, Attendance.date == day)
    return db.scalars(stmt).first()


def records_query(employee_id: int | None = None, start: date | None = None, end: date | None = None,
                  status: str | None = None, search: str | None = None,
                  department_id: int | None = None) -> Select:
    """Records in [start, end), newest first, with employee and department loaded."""
    stmt = select(Attendance).options(_WITH_EMPLOYEE)
    if search or department_id:
        stmt = stmt.join(Employee, Attendance.employee_id == Employee.id)
        if search:
            stmt = stmt.where(search_condition(search))
        if department_id:
            stmt = stmt.where(Employee.department_id == department_id)
    if status:
        stmt = stmt.where(Attendance.status == status)
    if employee_id:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    if start:
        stmt = stmt.where(Attendance.date >= start)
    if end:
        stmt = stmt.where(Attendance.date < end)
    return stmt.order_by(Attendance.date.desc(), Attendance.check_in.desc())


def list_for_date(db: Session, day: date) -> list[Attendance]:
    return list(db.scalars(select(Attendance).where(Attendance.date == day)))


def latest_checkins(db: Session, day: date, limit: int) -> list[Attendance]:
    stmt = (select(Attendance).options(_WITH_EMPLOYEE)
            .where(Attendance.date == day, Attendance.check_in.isnot(None))
            .order_by(Attendance.check_in.desc()).limit(limit))
    return list(db.scalars(stmt))


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Attendance))


def add(db: Session, record: Attendance) -> Attendance:
    """Stage a new record; it is written when the service commits (after all fields are set)."""
    db.add(record)
    return record
