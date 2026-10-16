"""Translations (gettext) and language-aware date/time formatting.

Usage in the UI:
    from core.i18n import _
    _("Employee Directory")                         # plain text
    _("Showing {start}-{end} of {total}").format(start=1, end=8, total=148)

Catalogs live in frontend/locales/<lang>/LC_MESSAGES/hrms.po (+ compiled .mo).
Update them with Babel (README > Translations has the full workflow):
    pybabel extract -k _ -k N_ --no-location --sort-output -o frontend/locales/hrms.pot frontend
    pybabel update -i frontend/locales/hrms.pot -d frontend/locales -D hrms
    pybabel compile -d frontend/locales -D hrms
"""
import gettext
from datetime import date, datetime, time
from pathlib import Path

DOMAIN = "hrms"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"
LANGUAGES = {"en": "English", "km": "ខ្មែរ"}
DEFAULT = "en"

_state = {"code": DEFAULT, "translation": gettext.NullTranslations()}

MONTHS_KM = ["មករា", "កុម្ភៈ", "មីនា", "មេសា", "ឧសភា", "មិថុនា",
             "កក្កដា", "សីហា", "កញ្ញា", "តុលា", "វិច្ឆិកា", "ធ្នូ"]
DAYS_KM = ["ច័ន្ទ", "អង្គារ", "ពុធ", "ព្រហស្បតិ៍", "សុក្រ", "សៅរ៍", "អាទិត្យ"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def set_language(code: str) -> None:
    code = code if code in LANGUAGES else DEFAULT
    _state["code"] = code
    _state["translation"] = (gettext.NullTranslations() if code == DEFAULT else
                             gettext.translation(DOMAIN, LOCALE_DIR, languages=[code], fallback=True))


def language() -> str:
    return _state["code"]


def is_khmer() -> bool:
    return _state["code"] == "km"


def _(message: str) -> str:
    """Translate a UI string into the current language."""
    text = _state["translation"].gettext(message)
    return safe_khmer(text) if _state["code"] == "km" else text


# Tk on Windows draws a string with one GDI call per font, and GDI garbles the end of some
# long Khmer runs (dotted circles, letters out of place). U+FEFF is invisible and not in the
# Khmer fonts, so Tk draws it with another font, which splits the run into short pieces.
_SPLIT = "﻿"
_COENG = "្"   # joins the next consonant below the current one: never split after it
SPLIT_EVERY = 16    # letter clusters


def safe_khmer(text: str) -> str:
    """Add invisible split points to long Khmer text so Windows draws it correctly."""
    if len(text) <= SPLIT_EVERY or _SPLIT in text:
        return text
    out, clusters, prev = [], 0, ""
    for ch in text:
        starts_cluster = "ក" <= ch <= "ឳ" and prev != _COENG  # consonant / independent vowel
        if starts_cluster and clusters >= SPLIT_EVERY:
            out.append(_SPLIT)
            clusters = 0
        if starts_cluster:
            clusters += 1
        elif not ("ក" <= ch <= "៿" or ch == " "):
            clusters = 0  # any other script already starts a new run
        out.append(ch)
        prev = ch
    return "".join(out)


def plain(text: str) -> str:
    """Text without the invisible split points (for files and the clipboard)."""
    return text.replace(_SPLIT, "")


def N_(message: str) -> str:
    """Mark a string for translation without translating it yet (translate later with _())."""
    return message


# ------------------------------------------------------------ date and time
def month_name(month: int, short: bool = False) -> str:
    if is_khmer():
        return MONTHS_KM[month - 1]
    name = MONTHS_EN[month - 1]
    return name[:3] if short else name


def day_name(day: date, short: bool = False) -> str:
    if is_khmer():
        return DAYS_KM[day.weekday()]
    name = DAYS_EN[day.weekday()]
    return name[:3] if short else name


def month_label(key: str) -> str:
    """'2026-10' -> 'October 2026' / 'តុលា 2026'."""
    y, m = map(int, key.split("-"))
    return f"{month_name(m)} {y}"


def format_date(d: date | str, style: str = "medium") -> str:
    """short: 'Oct 05' / '05 តុលា'   medium: 'Oct 05, 2026' / '05 តុលា 2026'."""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if is_khmer():
        return f"{d.day:02d} {month_name(d.month)}" + ("" if style == "short" else f" {d.year}")
    base = f"{month_name(d.month, short=True)} {d.day:02d}"
    return base if style == "short" else f"{base}, {d.year}"


def format_time(t: time | datetime | str | None, seconds: bool = False) -> str:
    """'09:05:00' -> '09:05 AM' / '09:05 ព្រឹក'."""
    if t is None or t == "":
        return "--"
    if isinstance(t, str):
        t = datetime.strptime(t, "%H:%M:%S").time()
    hour12 = t.hour % 12 or 12
    text = f"{hour12:02d}:{t.minute:02d}" + (f":{t.second:02d}" if seconds else "")
    return f"{text} {am_pm(t.hour)}"


def am_pm(hour: int) -> str:
    if is_khmer():
        return "ព្រឹក" if hour < 12 else "ល្ងាច"
    return "AM" if hour < 12 else "PM"
