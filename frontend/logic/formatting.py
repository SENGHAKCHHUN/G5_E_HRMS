"""Display formatting shared by the screens (no widgets, no data access)."""
from datetime import date, timedelta

from core import i18n
from core.state import state

LEAVE_TYPES = ["Annual", "Sick", "Casual", "Maternity/Paternity", "Unpaid"]


def money(value: float, sign: bool = False, symbol: str | None = None) -> str:
    """6130.5 -> '$6,130.50'; with sign=True -> '+$6,130.50' / '-$6,130.50'."""
    symbol = state.currency_symbol if symbol is None else symbol
    text = f"{symbol}{abs(value):,.2f}"
    if sign:
        return ("+" if value >= 0 else "-") + text
    return text if value >= 0 else "-" + text


def duration(seconds: float) -> str:
    """8h 07m (Khmer: 8ម៉ោង 07នាទី)."""
    seconds = max(0, int(seconds))
    hours, minutes = seconds // 3600, seconds % 3600 // 60
    if i18n.is_khmer():
        return f"{hours}ម៉ោង {minutes:02d}នាទី"
    return f"{hours}h {minutes:02d}m"


def recent_months(n: int = 3, today: date | None = None) -> list[str]:
    """The current month and the n-1 before it, newest first, as 'YYYY-MM'."""
    months, d = [], (today or date.today()).replace(day=1)
    for _i in range(n):
        months.append(d.strftime("%Y-%m"))
        d = (d - timedelta(days=1)).replace(day=1)
    return months


def month_label(key: str) -> str:
    return i18n.month_label(key)


def percent(part: float, whole: float) -> float:
    return part / whole * 100 if whole else 0.0
