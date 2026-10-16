"""Dashboard (Module 7): summary statistics, notifications and the summary PDF."""
from sqlalchemy.orm import Session

from ..core import clock
from ..core.i18n import t
from ..integrations import pdf
from ..models import User
from ..repositories import attendance_repo, department_repo, employee_repo, leave_repo, payroll_repo
from ..serializers import attendance_out, department_out
from .access import is_staff
from .settings_service import get_settings


def stats(db: Session) -> dict:
    today = clock.today(get_settings(db))
    emps = employee_repo.list_all(db)
    on_leave = sum(1 for e in emps if e.status == "On Leave")
    present = [a for a in attendance_repo.list_for_date(db, today) if a.check_in]
    expected = len(emps) - on_leave
    leave_types: dict[str, int] = {}
    for lv in leave_repo.approved_covering(db, today):
        leave_types[lv.type] = leave_types.get(lv.type, 0) + 1
    return {
        "total_employees": len(emps),
        "new_this_month": sum(1 for e in emps if e.hire_date >= today.replace(day=1)),
        "on_leave_today": on_leave,
        "leave_types": leave_types,
        "present": len(present),
        "on_time": sum(1 for a in present if a.status == "On Time"),
        "late": sum(1 for a in present if a.status == "Late"),
        "expected": expected,
        "attendance_rate": len(present) / expected * 100 if expected else 0,
        "pending_leaves": leave_repo.count(db, status="Pending"),
        "departments": [department_out(d) for d in department_repo.list_all(db)],
        "monthly_payroll": sum(e.salary for e in emps),
    }


def summary_pdf(db: Session, user: User) -> bytes:
    return pdf.summary_pdf(stats(db), get_settings(db), user.username)


def recent_checkins(db: Session, limit: int) -> list[dict]:
    today = clock.today(get_settings(db))
    return [attendance_out(a) for a in attendance_repo.latest_checkins(db, today, limit)]


def notifications(db: Session, user: User) -> list[str]:
    """Short alerts for the bell menu, based on live data."""
    out = []
    today = clock.today(get_settings(db))
    if is_staff(user):
        pending = leave_repo.count(db, status="Pending")
        if pending:
            out.append(t("{count} leave request(s) are awaiting approval", count=pending))
        unpaid = payroll_repo.count(db, month=today.strftime("%Y-%m"), exclude_status="Paid")
        if unpaid:
            out.append(t("{count} payroll line(s) for this month are not yet paid", count=unpaid))
        probation = employee_repo.count(db, status="Probation")
        if probation:
            out.append(t("{count} employee(s) are on probation", count=probation))
    else:
        mine = leave_repo.count(db, status="Pending", employee_id=user.employee_id)
        if mine:
            out.append(t("{count} of your leave request(s) are pending", count=mine))
        if attendance_repo.get_for_day(db, user.employee_id, today) is None:
            out.append(t("You have not checked in today"))
    return out or [t("You're all caught up")]
