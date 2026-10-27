"""Attendance rules as pure functions (no database), used by the attendance service and day closing.

Check-in rules (all configurable in Settings > Attendance & Policies):
  1. The time always comes from the server clock - the client's clock is ignored.
  2. Check-in is only accepted inside the window [checkin_open, checkin_close].
  3. Check-in is refused on days that are not in the configured work week.
  4. With restrict_network on, punches are only accepted from office networks
     (office_networks), except employees whose work mode is "Remote" when
     remote_exempt is on.
  5. A check-out before checkout_cutoff (e.g. 01:30 < 04:00) closes the previous
     day's open record, so a shift may end after midnight.
  6. Worked less than half_day_hours = "Half Day".
"""
from datetime import datetime, time, timedelta
from ipaddress import ip_address, ip_network

from ..models import Attendance, Employee


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


def checkout_status(rec: Attendance, settings: dict) -> str:
    """Status once the day is closed: Half Day if too little was worked, else the check-in status."""
    hours = float(settings["half_day_hours"])
    if hours and rec.check_in and rec.check_out and worked_seconds(rec, None) < hours * 3600:
        return "Half Day"
    return rec.status


def _in_overnight_grace(now: datetime, settings: dict) -> bool:
    """True between midnight and checkout_cutoff, when a check-out still belongs to yesterday.

    The grace ends early when check-in opens first, so a check-in and a check-out never compete.
    """
    return now.time() < min(_hm(settings["checkout_cutoff"]), _hm(settings["checkin_open"]))


def worked_seconds(rec: Attendance, now: datetime | None) -> float:
    """Time between check-in and check-out (or now, for an open record of the last 24 hours).

    A check-out earlier than the check-in was made after midnight (rule 5).
    """
    if rec.check_in is None:
        return 0
    start = datetime.combine(rec.date, rec.check_in)
    if rec.check_out is not None:
        end = datetime.combine(rec.date, rec.check_out)
        if end < start:
            end += timedelta(days=1)
    elif now is not None and start <= now < start + timedelta(days=1):
        end = now
    else:
        return 0
    return max(0.0, (end - start).total_seconds())
