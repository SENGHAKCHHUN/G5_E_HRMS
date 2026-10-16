"""Attendance (Module 4): self check-in/check-out with server-side rules, logs, manual entries.

Check-in rules (all configurable in Settings > Attendance & Policies):
  1. The time always comes from the server clock - the client's clock is ignored.
  2. Check-in is only accepted inside the window [checkin_open, checkin_close].
  3. Check-in is refused on days that are not in the configured work week.
  4. With restrict_network on, punches are only accepted from office networks
     (office_networks), except employees whose work mode is "Remote" when
     remote_exempt is on.
HR / Admin can always fix a missed punch with a manual log entry.
"""
from datetime import date, datetime, time, timedelta
from ipaddress import ip_address, ip_network

from sqlalchemy.orm import Session

from ..core import clock, i18n
from ..core.errors import BadRequest, Conflict, Forbidden, NotFound
from ..core.pagination import ALL, Page
from ..models import Attendance, Employee, User
from ..repositories import attendance_repo, audit_repo, employee_repo, leave_repo
from ..repositories.paging import paginate
from ..serializers import attendance_out
from .access import ensure_self_or_staff, scope_employee
from .settings_service import get_settings


def _hm(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def on_office_network(ip: str, networks: str) -> bool:
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    for part in (p.strip() for p in networks.split(",")):
        if part:
            try:
                if addr in ip_network(part, strict=False):
                    return True
            except ValueError:
                continue
    return False


def evaluate_policy(emp: Employee | None, ip: str, settings: dict, now: datetime) -> dict:
    """Pure rule evaluation: what the punch rules say for this employee/device at `now`."""
    exempt = bool(emp and settings["remote_exempt"] and emp.work_mode == "Remote")
    on_network = on_office_network(ip, settings["office_networks"])
    return {
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "restrict_network": settings["restrict_network"],
        "on_office_network": on_network,
        "remote_exempt": exempt,
        "network_ok": (not settings["restrict_network"]) or exempt or on_network,
        "checkin_open": settings["checkin_open"],
        "checkin_close": settings["checkin_close"],
        "window_open": _hm(settings["checkin_open"]) <= now.time() <= _hm(settings["checkin_close"]),
        "work_day": now.strftime("%a") in settings["work_week"],
        "shift_start": settings["shift_start"],
        "grace_minutes": settings["grace_minutes"],
    }


def punch_status(now: datetime, settings: dict) -> str:
    late_after = datetime.combine(now.date(), _hm(settings["shift_start"])) + \
        timedelta(minutes=int(settings["grace_minutes"]))
    return "Late" if now > late_after else "On Time"


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
    today = clock.today(get_settings(db))
    rec = attendance_repo.get_for_day(db, emp.id, today)
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
    rec = attendance_repo.get_for_day(db, emp.id, now.date())
    if rec is None or rec.check_in is None:
        raise Conflict("You have not checked in today")
    if rec.check_out:
        raise Conflict("Already checked out today at {time}", time=i18n.format_time(rec.check_out))
    rec.check_out = now.time()
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
    stmt = attendance_repo.records_query(employee_id, start, end, status, search, department_id)
    rows, total = paginate(db, stmt, page)
    return [attendance_out(a) for a in rows], total


def worked_seconds(rec: Attendance, now: datetime) -> float:
    """Time between check-in and check-out (or now, for today's open record)."""
    if rec.check_in is None:
        return 0
    if rec.check_out is not None:
        end = rec.check_out
    elif rec.date == now.date():
        end = now.time()
    else:
        return 0
    seconds = (datetime.combine(rec.date, end) - datetime.combine(rec.date, rec.check_in)).total_seconds()
    return max(0.0, seconds)


def summary(db: Session, user: User, employee_id: int | None, month: str | None) -> dict:
    """Totals for the attendance cards: punctuality counts and average hours of completed shifts."""
    employee_id = scope_employee(user, employee_id)
    ensure_self_or_staff(user, employee_id)
    start, end = _month_range(month)
    rows, _total = paginate(db, attendance_repo.records_query(employee_id, start, end))
    now = clock.now(get_settings(db))
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
    if cin and cout and cout < cin:
        raise BadRequest("Check-out cannot be before check-in")
    rec = attendance_repo.get_for_day(db, emp.id, day)
    if rec is None:
        rec = attendance_repo.add(db, Attendance(employee_id=emp.id, date=day))
    rec.check_in, rec.check_out, rec.status, rec.source = cin, cout, status, "manual"
    audit_repo.add(db, actor.username, "MANUAL", f"Attendance for {emp.code} on {day} set to {status}")
    db.commit()
    db.refresh(rec)
    return attendance_out(rec)
