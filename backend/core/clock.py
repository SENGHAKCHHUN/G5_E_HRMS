"""Server-side "now" in the timezone configured in Settings.

The timezone setting is a label like "(UTC+07:00) Bangkok, Hanoi, Phnom Penh"; the
UTC offset in brackets is used (fixed offset, no daylight-saving changes). If the
label has no offset, the server machine's local time is used.
"""
import re
from datetime import date, datetime, timedelta, timezone

_OFFSET = re.compile(r"UTC([+-])(\d{1,2}):(\d{2})")


def tz_from_label(label: str) -> timezone | None:
    m = _OFFSET.search(label or "")
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))


def now(settings: dict) -> datetime:
    """Naive datetime in the configured timezone (what gets stored and compared)."""
    tz = tz_from_label(settings.get("timezone", ""))
    if tz is None:
        return datetime.now().replace(microsecond=0)
    return datetime.now(tz).replace(tzinfo=None, microsecond=0)


def today(settings: dict) -> date:
    return now(settings).date()
