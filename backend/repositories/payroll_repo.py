"""Database access for payroll lines."""
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Employee, Payroll
from .employee_repo import search_condition


def get(db: Session, payroll_id: int) -> Payroll | None:
    return db.get(Payroll, payroll_id)


def lines_query(month: str | None = None, employee_id: int | None = None, status: str | None = None,
                search: str | None = None, department_id: int | None = None) -> Select:
    stmt = select(Payroll).options(joinedload(Payroll.employee).joinedload(Employee.department))
    if search or department_id:
        stmt = stmt.join(Employee, Payroll.employee_id == Employee.id)
        if search:
            stmt = stmt.where(search_condition(search))
        if department_id:
            stmt = stmt.where(Employee.department_id == department_id)
    if status:
        stmt = stmt.where(Payroll.status == status)
    if month:
        stmt = stmt.where(Payroll.month == month)
    if employee_id:
        stmt = stmt.where(Payroll.employee_id == employee_id)
    return stmt.order_by(Payroll.month.desc(), Payroll.employee_id)


def totals(db: Session, month: str | None = None, employee_id: int | None = None) -> dict:
    """Sums and per-status counts for the payroll summary cards."""
    stmt = select(func.count(), func.coalesce(func.sum(Payroll.base_salary + Payroll.bonus), 0),
                  func.coalesce(func.sum(Payroll.tax), 0), func.coalesce(func.sum(Payroll.net_salary), 0))
    by_status = select(Payroll.status, func.count()).group_by(Payroll.status)
    if month:
        stmt, by_status = stmt.where(Payroll.month == month), by_status.where(Payroll.month == month)
    if employee_id:
        stmt = stmt.where(Payroll.employee_id == employee_id)
        by_status = by_status.where(Payroll.employee_id == employee_id)
    count, gross, tax, net = db.execute(stmt).one()
    return {"count": count, "gross": float(gross), "tax": float(tax), "net": float(net),
            "by_status": dict(db.execute(by_status).all())}


def by_employee_for_month(db: Session, month: str) -> dict[int, Payroll]:
    return {p.employee_id: p for p in db.scalars(select(Payroll).where(Payroll.month == month))}


def with_status(db: Session, month: str, status: str) -> list[Payroll]:
    return list(db.scalars(select(Payroll).where(Payroll.month == month, Payroll.status == status)))


def count(db: Session, month: str | None = None, exclude_status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Payroll)
    if month:
        stmt = stmt.where(Payroll.month == month)
    if exclude_status:
        stmt = stmt.where(Payroll.status != exclude_status)
    return db.scalar(stmt)


def add(db: Session, line: Payroll) -> Payroll:
    db.add(line)
    return line
