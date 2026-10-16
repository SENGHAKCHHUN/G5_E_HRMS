"""Database access for leave requests."""
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Employee, LeaveRequest


def get(db: Session, leave_id: int) -> LeaveRequest | None:
    return db.get(LeaveRequest, leave_id)


def requests_query(employee_id: int | None = None, status: str | None = None) -> Select:
    stmt = select(LeaveRequest).options(joinedload(LeaveRequest.employee).joinedload(Employee.department))
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    if employee_id:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    return stmt.order_by(LeaveRequest.id.desc())


def approved_of_type(db: Session, employee_id: int, leave_type: str) -> list[LeaveRequest]:
    stmt = select(LeaveRequest).where(LeaveRequest.employee_id == employee_id, LeaveRequest.type == leave_type,
                                      LeaveRequest.status == "Approved")
    return list(db.scalars(stmt))


def approved_covering(db: Session, day: date, employee_id: int | None = None) -> list[LeaveRequest]:
    """Approved requests whose period includes `day` (optionally for one employee)."""
    stmt = select(LeaveRequest).where(LeaveRequest.status == "Approved", LeaveRequest.start_date <= day,
                                      LeaveRequest.end_date >= day)
    if employee_id is not None:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    return list(db.scalars(stmt))


def first_overlapping(db: Session, employee_id: int, start: date, end: date) -> LeaveRequest | None:
    stmt = select(LeaveRequest).where(
        LeaveRequest.employee_id == employee_id, LeaveRequest.status.in_(["Pending", "Approved"]),
        LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)
    return db.scalars(stmt).first()


def count(db: Session, status: str | None = None, employee_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(LeaveRequest)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    if employee_id is not None:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    return db.scalar(stmt)


def add(db: Session, leave: LeaveRequest) -> LeaveRequest:
    db.add(leave)
    db.flush()
    return leave
