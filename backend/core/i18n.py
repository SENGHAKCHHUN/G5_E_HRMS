"""Server-side translations (gettext) chosen per request from the Accept-Language header.

Messages are written in English as templates and translated when they are sent:
    raise Conflict("Already checked in today at {time}", time=...)
    t("{count} leave request(s) are awaiting approval", count=4)

Catalogs: backend/locales/<lang>/LC_MESSAGES/api.po (+ compiled .mo), managed with Babel
(see README > Translations). Machine-readable codes such as "otp_required" are never
translated because they have no catalog entry.
"""
import gettext
from contextvars import ContextVar
from datetime import datetime, time
from pathlib import Path

DOMAIN = "api"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"
SUPPORTED = ("en", "km")
_language: ContextVar[str] = ContextVar("language", default="en")
_catalogs: dict[str, gettext.NullTranslations] = {}

DAYS_KM = ["ច័ន្ទ", "អង្គារ", "ពុធ", "ព្រហស្បតិ៍", "សុក្រ", "សៅរ៍", "អាទិត្យ"]
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_KM = ["មករា", "កុម្ភៈ", "មីនា", "មេសា", "ឧសភា", "មិថុនា", "កក្កដា", "សីហា", "កញ្ញា", "តុលា",
             "វិច្ឆិកា", "ធ្នូ"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]


def parse_accept_language(header: str | None) -> str:
    """'km-KH,km;q=0.9,en;q=0.8' -> 'km'. Unknown or missing -> 'en'."""
    for part in (header or "").split(","):
        code = part.split(";")[0].strip().lower().split("-")[0]
        if code in SUPPORTED:
            return code
    return "en"


def set_language(code: str) -> None:
    _language.set(code if code in SUPPORTED else "en")


def language() -> str:
    return _language.get()


def _catalog(code: str) -> gettext.NullTranslations:
    if code not in _catalogs:
        _catalogs[code] = (gettext.NullTranslations() if code == "en" else
                           gettext.translation(DOMAIN, LOCALE_DIR, languages=[code], fallback=True))
    return _catalogs[code]


def gettext_(message: str) -> str:
    return _catalog(language()).gettext(message)


def t(template: str, **params) -> str:
    """Translate a message template, then fill in its {placeholders}.
    Text values that have their own catalog entry (e.g. 'Annual') are translated too."""
    if not params:
        return gettext_(template)
    values = {k: gettext_(v) if isinstance(v, str) else v for k, v in params.items()}
    return gettext_(template).format(**values)


def N_(message: str) -> str:
    """Mark a string for translation without translating it here."""
    return message


def day_name(when: datetime) -> str:
    return (DAYS_KM if language() == "km" else DAYS_EN)[when.weekday()]


def month_name(month: int) -> str:
    return (MONTHS_KM if language() == "km" else MONTHS_EN)[month - 1]


def format_time(value: time | datetime) -> str:
    hour12 = value.hour % 12 or 12
    suffix = ("ព្រឹក" if value.hour < 12 else "ល្ងាច") if language() == "km" else ("AM" if value.hour < 12 else "PM")
    return f"{hour12:02d}:{value.minute:02d} {suffix}"
