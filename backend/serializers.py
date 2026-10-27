"""Convert ORM objects to the JSON shapes the desktop frontend expects."""
import calendar
from datetime import date, time

from .core.clock import working_days
from .models import Attendance, Department, Employee, LeaveRequest, Payroll, Position, Requisition


def _t(value: time | None) -> str | None:
    return value.strftime("%H:%M:%S") if value else None


def employee_out(e: Employee) -> dict:
    return {
        "id": e.id, "code": e.code, "first_name": e.first_name, "last_name": e.last_name,
        "full_name": e.full_name, "email": e.email, "phone": e.phone, "gender": e.gender,
        "hire_date": e.hire_date.isoformat(),
        "termination_date": e.termination_date.isoformat() if e.termination_date else None, "position": e.position, "salary": e.salary,
        "department_id": e.department_id, "department": e.department.name if e.department else "-",
        "status": e.status, "employment": e.employment, "work_mode": e.work_mode, "shift": e.shift,
        "role": e.user.role if e.user else None,
    }


def department_out(d: Department) -> dict:
    today = date.today()
    return {
        "id": d.id, "name": d.name, "description": d.description, "code": d.code, "lead": d.lead,
        "location": d.location, "budget": d.budget, "target": d.target, "icon": d.icon,
        "headcount": len(d.employees), "roles": len(d.positions),
        "payroll": sum(e.salary for e in d.employees),
        # calculated from the employees' hire dates and salaries
        "avg_seniority": round(sum((today - e.hire_date).days for e in d.employees) / 365.25 / len(d.employees), 1)
        if d.employees else 0.0,
        "avg_salary": round(sum(e.salary for e in d.employees) / len(d.employees)) if d.employees else 0,
    }


def position_out(p: Position, headcount: int) -> dict:
    return {
        "id": p.id, "department_id": p.department_id, "title": p.title, "grade": p.grade,
        "min_salary": p.min_salary, "max_salary": p.max_salary, "skills": p.skills,
        "planned": p.planned, "headcount": headcount,
    }


def _person(e: Employee) -> dict:
    return {"employee": e.full_name, "code": e.code, "first_name": e.first_name,
            "last_name": e.last_name, "department": e.department.name if e.department else "-"}


def attendance_out(a: Attendance) -> dict:
    return {
        "id": a.id, "employee_id": a.employee_id, "date": a.date.isoformat(),
        "check_in": _t(a.check_in), "check_out": _t(a.check_out), "status": a.status,
        "source": a.source, "shift": a.employee.shift, **_person(a.employee),
    }


def leave_out(lv: LeaveRequest, work_week: list[str]) -> dict:
    """days = working days in the request (the work week in Settings)."""
    return {
        "id": lv.id, "employee_id": lv.employee_id, "type": lv.type,
        "start_date": lv.start_date.isoformat(), "end_date": lv.end_date.isoformat(),
        "reason": lv.reason, "status": lv.status, "review_note": lv.review_note,
        "days": len(working_days(lv.start_date, lv.end_date, work_week)), **_person(lv.employee),
    }


def payroll_out(p: Payroll) -> dict:
    e = p.employee
    return {
        "id": p.id, "employee_id": p.employee_id, "month": p.month, "base_salary": p.base_salary,
        "bonus": p.bonus, "adjustment": p.adjustment or 0.0, "note": p.note or "", "paid_days": p.paid_days,
        "month_days": calendar.monthrange(int(p.month[:4]), int(p.month[5:7]))[1],
        "unpaid_days": p.unpaid_days or 0.0, "unpaid_deduction": p.unpaid_deduction or 0.0,
        "overtime_hours": p.overtime_hours or 0.0, "overtime_pay": p.overtime_pay or 0.0, "tax": p.tax, "insurance": p.insurance, "pension": p.pension,
        "deductions": p.deductions, "net_salary": p.net_salary, "status": p.status,
        "email": e.email, "position": e.position, **_person(e),
    }


def requisition_out(r: Requisition) -> dict:
    return {"id": r.id, "code": f"REQ-{r.id:04d}", "department_id": r.department_id,
            "position_id": r.position_id, "title": r.title, "openings": r.openings, "note": r.note,
            "status": r.status, "created_by": r.created_by, "created_at": r.created_at.strftime("%Y-%m-%d")}
