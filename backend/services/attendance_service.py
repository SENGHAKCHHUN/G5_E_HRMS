"""Attendance (Module 4): self check-in/check-out with server-side rules, logs, manual entries.

The rules live in two files next to this one:
    attendance_rules.py    check-in rules 1-6 (pure functions)
    attendance_closing.py  day closing rules 7-8 (auto Absent, forgotten check-outs)
HR / Admin can always fix a missed punch with a manual log entry.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from ..core import clock, i18n
from ..core.errors import BadRequest, Conflict, Forbidden, NotFound
from ..core.pagination import ALL, Page
from ..models import Attendance, Employee, User
from ..repositories import attendance_repo, audit_repo, employee_repo, leave_repo
from ..repositories.paging import paginate
from ..serializers import attendance_out
from .access import ensure_self_or_staff, scope_employee
from .attendance_closing import CLOSED_THROUGH, close_days  # noqa: F401 - CLOSED_THROUGH: used by tests
from .attendance_rules import (_hm, _in_overnight_grace, checkout_status, evaluate_policy,  # noqa: F401
                               on_office_network, punch_status, worked_seconds)
from .settings_service import get_settings


def _open_record(db: Session, emp: Employee, now: datetime, settings: dict) -> Attendance | None:
    """Today's record, or yesterday's still-open one just after midnight."""
    rec = attendance_repo.get_for_day(db, emp.id, now.date())
    if (rec is None or rec.check_in is None) and _in_overnight_grace(now, settings):
        prev = attendance_repo.get_for_day(db, emp.id, now.date() - timedelta(days=1))
        if prev and prev.check_in and prev.check_out is None:
            return prev
    return rec


def _my_employee(user: User) -> Employee:
    if user.employee is None:
        raise BadRequest("Your account is not linked to an employee record")
    return user.employee


def _on_leave(db: Session, emp: Employee, day: date) -> bool:
    return emp.status == "On Leave" or bool(leave_repo.approved_covering(db, day, employee_id=emp.id))


def _require_network(policy: dict):
    if not policy["network_ok"]:
        raise Forbidden("Check-in/out is only allowed from the office network (this device: {ip}). "
                        "Ask HR for a manual entry if you are working elsewhere.", ip=policy["ip"] or "?")


def get_policy(db: Session, user: User, ip: str) -> dict:
    settings = get_settings(db)
    return evaluate_policy(user.employee, ip, settings, clock.now(settings))


def today_record(db: Session, user: User) -> dict | None:
    emp = _my_employee(user)
    settings = get_settings(db)
    now = clock.now(settings)
    close_days(db, settings, now)
    today = now.date()
    rec = _open_record(db, emp, now, settings)
    if rec:
        return attendance_out(rec)
    if _on_leave(db, emp, today):
        return {"employee_id": emp.id, "date": today.isoformat(), "check_in": None,
                "check_out": None, "status": "On Leave"}
    return None


def check_in(db: Session, user: User, ip: str) -> dict:
    emp = _my_employee(user)
    settings = get_settings(db)
    now = clock.now(settings)
    policy = evaluate_policy(emp, ip, settings, now)
    _require_network(policy)
    close_days(db, settings, now)
    if _on_leave(db, emp, now.date()):
        raise Conflict("You are on approved leave today")
    if not policy["work_day"]:
        raise Forbidden("{day} is not a working day. Ask HR for a manual entry if you worked today.",
                        day=i18n.day_name(now))
    if not policy["window_open"]:
        raise Forbidden("Check-in is only allowed between {open} and {close} (server time now {now}). "
                        "Ask HR for a manual entry.", open=settings["checkin_open"],
                        close=settings["checkin_close"], now=f"{now:%H:%M}")
    rec = attendance_repo.get_for_day(db, emp.id, now.date())
    if rec and rec.check_in:
        raise Conflict("Already checked in today at {time}", time=i18n.format_time(rec.check_in))
    if rec is None:
        rec = attendance_repo.add(db, Attendance(employee_id=emp.id, date=now.date()))
    rec.check_in = now.time()
    rec.check_out = None
    rec.status = punch_status(now, settings)
    rec.source = "self"
    rec.ip_address = ip
    db.commit()
    db.refresh(rec)
    return attendance_out(rec)


def check_out(db: Session, user: User, ip: str) -> dict:
    emp = _my_employee(user)
    settings = get_settings(db)
    now = clock.now(settings)
    _require_network(evaluate_policy(emp, ip, settings, now))
    close_days(db, settings, now)
    rec = _open_record(db, emp, now, settings)
    if rec is None or rec.check_in is None:
        raise Conflict("You have not checked in today")
    if rec.check_out:
        raise Conflict("Already checked out today at {time}", time=i18n.format_time(rec.check_out))
    rec.check_out = now.time()
    rec.status = checkout_status(rec, settings)
    db.commit()
    db.refresh(rec)
    return attendance_out(rec)


def _month_range(month: str | None) -> tuple[date | None, date | None]:
    if not month:
        return None, None
    try:
        start = datetime.strptime(month, "%Y-%m").date()
    except ValueError:
        raise BadRequest("month must be YYYY-MM")
    return start, (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def list_for(db: Session, user: User, employee_id: int | None, month: str | None, page: Page = ALL,
             status: str | None = None, search: str | None = None,
             department_id: int | None = None) -> tuple[list[dict], int]:
    """month = 'YYYY-MM'. Employees always get only their own records."""
    employee_id = scope_employee(user, employee_id)
    ensure_self_or_staff(user, employee_id)
    start, end = _month_range(month)
    settings = get_settings(db)
    close_days(db, settings, clock.now(settings))
    stmt = attendance_repo.records_query(employee_id, start, end, status, search, department_id)
    rows, total = paginate(db, stmt, page)
    return [attendance_out(a) for a in rows], total


def summary(db: Session, user: User, employee_id: int | None, month: str | None) -> dict:
    """Totals for the attendance cards: punctuality counts and average hours of completed shifts."""
    employee_id = scope_employee(user, employee_id)
    ensure_self_or_staff(user, employee_id)
    start, end = _month_range(month)
    settings = get_settings(db)
    now = clock.now(settings)
    close_days(db, settings, now)
    rows, _total = paginate(db, attendance_repo.records_query(employee_id, start, end))
    completed = [r for r in rows if r.check_in and r.check_out]
    counts = {s: sum(1 for r in rows if r.status == s) for s in ("On Time", "Late", "Absent", "Half Day", "On Leave")}
    return {
        "records": len(rows),
        "worked_days": sum(1 for r in rows if r.check_in),
        "on_time": counts["On Time"], "late": counts["Late"], "absent": counts["Absent"],
        "half_day": counts["Half Day"], "on_leave": counts["On Leave"],
        "completed_shifts": len(completed),
        "avg_seconds": (sum(worked_seconds(r, now) for r in completed) / len(completed)) if completed else 0,
    }


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return datetime.strptime(value if len(value) == 8 else value + ":00", "%H:%M:%S").time()


def manual_entry(db: Session, actor: User, employee_id: int, day: date, check_in_at: str | None,
                 check_out_at: str | None, status: str) -> dict:
    """HR/Admin: record or correct a day's punches (replaces that day's record)."""
    emp = employee_repo.get(db, employee_id)
    if emp is None:
        raise NotFound("Employee not found")
    cin, cout = (None, None) if status == "Absent" else (_parse_time(check_in_at), _parse_time(check_out_at))
    # a check-out earlier than the cutoff was made after midnight (rule 5)
    if cin and cout and cout < cin and cout >= _hm(get_settings(db)["checkout_cutoff"]):
        raise BadRequest("Check-out cannot be before check-in")
    rec = attendance_repo.get_for_day(db, emp.id, day)
    if rec is None:
        rec = attendance_repo.add(db, Attendance(employee_id=emp.id, date=day))
    rec.check_in, rec.check_out, rec.status, rec.source = cin, cout, status, "manual"
    audit_repo.add(db, actor.username, "MANUAL", f"Attendance for {emp.code} on {day} set to {status}")
    db.commit()
    db.refresh(rec)
    return attendance_out(rec)


# ------------------------------------------------------------ closing days
