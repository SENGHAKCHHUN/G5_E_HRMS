"""Leave rules used by the Leave screen (validated again by the server)."""
from datetime import date, timedelta

from core import i18n
from core.i18n import _

STATUS_KIND = {"Pending": "warning", "Approved": "success", "Rejected": "danger"}
WORK_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri"]  # used when the server settings are not loaded


def days_between(start: str, end: str, work_week: list[str] | None = None) -> int:
    """Working days from start to end (both included); negative when end is before start."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    if e < s:
        return (e - s).days
    week = work_week or WORK_WEEK
    return sum(1 for i in range((e - s).days + 1) if (s + timedelta(days=i)).strftime("%a") in week)


def period_text(start: str, end: str) -> str:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    if s == e:
        return i18n.format_date(s)
    if (s.year, s.month) == (e.year, e.month):  # compact: Khmer month names are long
        if i18n.is_khmer():
            return f"{s.day:02d} - {i18n.format_date(e)}"
        return f"{i18n.format_date(s, 'short')} - {e.day:02d}, {e.year}"
    return f"{i18n.format_date(s, 'short')} - {i18n.format_date(e)}"


def translate_type(leave_type: str) -> str:
    return {"Annual": _("Annual"), "Sick": _("Sick"), "Casual": _("Casual"),
            "Maternity/Paternity": _("Maternity/Paternity"), "Unpaid": _("Unpaid")}.get(leave_type, leave_type)


def translate_status(status: str) -> str:
    return {"Pending": _("Pending"), "Approved": _("Approved"), "Rejected": _("Rejected")}.get(status, status)


def validate_request(start: str, end: str, leave_type: str, balance: dict,
                     work_week: list[str] | None = None) -> tuple[int, str | None]:
    """(number of working days, error message or None) for a new leave request."""
    try:
        days = days_between(start, end, work_week)
    except ValueError:
        return 0, _("Dates must be in YYYY-MM-DD format.")
    if days < 0:
        return days, _("End date is before start date")
    if days == 0:
        return days, _("The selected dates contain no working days.")
    remaining = balance.get(leave_type, {}).get("remaining")
    if remaining is not None and days > remaining:
        return days, _("Only {remaining} day(s) of {leave_type} leave remaining.").format(
            remaining=remaining, leave_type=translate_type(leave_type))
    return days, None
