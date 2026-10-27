"""Closing a day (close_days, run before attendance is read or punched).

  7. auto_absent: an employee with no record once check-in has closed on a working
     day (and not on leave) gets an "Absent" record.
  8. auto_checkout: a check-out still missing after the day is over is set to
     shift_end. Both kinds of record get source "auto" so HR can review them.
"""
import threading
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Attendance
from ..repositories import attendance_repo, employee_repo, leave_repo, setting_repo
from .attendance_rules import _hm, _in_overnight_grace, checkout_status


CLOSED_THROUGH = "attendance_closed_through"  # last day checked for no-shows (stored setting)


_closing = threading.Lock()


def _day_over(day: date, now: datetime, settings: dict) -> bool:
    """The day's check-out can no longer be made (the after-midnight grace included)."""
    after = day + timedelta(days=1)
    return now.date() > after or (now.date() == after and not _in_overnight_grace(now, settings))


def _absent_days(db: Session, now: datetime, settings: dict) -> list[date]:
    """Days not yet checked for no-shows, up to the last one whose check-in window has closed.

    The first run starts at today, so days from before this rule existed are left alone.
    """
    stored = setting_repo.load_all(db).get(CLOSED_THROUGH)
    last = now.date() if now.time() > _hm(settings["checkin_close"]) else now.date() - timedelta(days=1)
    first = date.fromisoformat(stored) + timedelta(days=1) if stored else now.date()
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def close_days(db: Session, settings: dict, now: datetime) -> None:
    """Apply the day closing rules (7, 8) to every day that has ended since the last run."""
    with _closing:
        try:
            if _close_days(db, settings, now):
                db.commit()
        except IntegrityError:  # another server process closed the same day at the same moment
            db.rollback()


def _close_days(db: Session, settings: dict, now: datetime) -> bool:
    changed = False
    if settings["auto_checkout"]:
        shift_end = _hm(settings["shift_end"])
        for rec in attendance_repo.open_before(db, now.date()):
            if _day_over(rec.date, now, settings):
                rec.check_out = max(shift_end, rec.check_in)
                rec.status = checkout_status(rec, settings)
                rec.source = "auto"
                changed = True
    days = _absent_days(db, now, settings)
    if settings["auto_absent"]:
        employees = [e for e in employee_repo.list_all(db) if e.status not in ("Terminated", "On Leave")]
        for day in days:
            if day.strftime("%a") not in settings["work_week"]:
                continue
            marked = {a.employee_id for a in attendance_repo.list_for_date(db, day)}
            marked |= {lv.employee_id for lv in leave_repo.approved_covering(db, day)}
            for emp in employees:
                if emp.id not in marked and emp.hire_date <= day:
                    attendance_repo.add(db, Attendance(employee_id=emp.id, date=day, status="Absent",
                                                       source="auto"))
                    changed = True
    if days:
        setting_repo.save(db, CLOSED_THROUGH, days[-1].isoformat())
        changed = True
    return changed
