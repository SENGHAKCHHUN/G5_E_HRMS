"""Attendance calculations used by the Attendance screen and the clock card."""
from datetime import date, datetime, timedelta

from core.i18n import _

STATUS_KIND = {"On Time": "success", "Late": "danger", "Absent": "danger", "Half Day": "warning",
               "On Leave": "neutral"}


def _parse(hms: str) -> datetime:
    return datetime.strptime(hms, "%H:%M:%S")


def _at(day: str, hms: str) -> datetime:
    return datetime.strptime(f"{day} {hms}", "%Y-%m-%d %H:%M:%S")


def _span(rec: dict) -> tuple[datetime, datetime]:
    """Check-in and check-out as datetimes; a check-out earlier than the check-in was after midnight."""
    start, end = _at(rec["date"], rec["check_in"]), _at(rec["date"], rec["check_out"])
    return start, end + timedelta(days=1) if end < start else end


def worked_seconds(rec: dict, now: datetime | None = None) -> float:
    """Seconds between check-in and check-out; for an open record of the last 24 hours, until `now`."""
    if not rec.get("check_in"):
        return 0
    if rec.get("check_out"):
        start, end = _span(rec)
    else:
        now = now or datetime.now()
        start, end = _at(rec["date"], rec["check_in"]), now
        if not start <= now < start + timedelta(days=1):
            return 0
    return max(0.0, (end - start).total_seconds())


def overtime_seconds(rec: dict, overtime_after: str = "18:00") -> float:
    """Time worked after the 'overtime after' hour (Settings); half days never count."""
    if not rec.get("check_out") or rec.get("status") == "Half Day":
        return 0
    start, end = _span(rec)
    after = _at(rec["date"], overtime_after + ":00")
    return max(0.0, (end - max(after, start)).total_seconds())


def late_minutes(rec: dict, shift_start: str = "09:00") -> int:
    if rec.get("status") != "Late" or not rec.get("check_in"):
        return 0
    return max(0, int((_parse(rec["check_in"]) - datetime.strptime(shift_start, "%H:%M")).total_seconds() // 60))


def status_label(rec: dict, shift_start: str = "09:00") -> str:
    """'Late (22m)' / 'On Time' ... in the current language."""
    status = rec.get("status", "")
    if status == "Late" and rec.get("check_in"):
        return _("Late ({minutes}m)").format(minutes=late_minutes(rec, shift_start))
    return translate_status(status)


def translate_status(status: str) -> str:
    return {"On Time": _("On Time"), "Late": _("Late"), "Absent": _("Absent"), "Half Day": _("Half Day"),
            "On Leave": _("On Leave")}.get(status, status)


def in_progress(rec: dict, today: date | None = None) -> bool:
    """Checked in and not yet out, today or (for a shift past midnight) yesterday."""
    today = today or date.today()
    return bool(rec.get("check_in") and not rec.get("check_out")
                and rec.get("date") in (today.isoformat(), (today - timedelta(days=1)).isoformat()))


def punctuality(summary: dict) -> float:
    """Share of worked days that started on time (0-100)."""
    worked = summary.get("worked_days", 0)
    return summary.get("on_time", 0) / worked * 100 if worked else 0.0
