"""Translation catalogs: every string in the code has a Khmer translation with the same placeholders."""
import re
import string
from pathlib import Path

import pytest
from babel.messages.extract import extract_from_dir
from babel.messages.mofile import read_mo
from babel.messages.pofile import read_po

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = [
    (ROOT / "frontend", ROOT / "frontend/locales/km/LC_MESSAGES/hrms"),
    (ROOT / "backend", ROOT / "backend/locales/km/LC_MESSAGES/api"),
]
# backend messages are also the first argument of the DomainError classes (backend/core/errors.py)
KEYWORDS = dict.fromkeys(["_", "N_", "gettext_", "t", "DomainError", "BadRequest", "Unauthorized", "Forbidden",
                          "NotFound", "Conflict", "TooManyRequests", "ExternalServiceError"])


def _source_messages(folder: Path) -> set[str]:
    found = extract_from_dir(str(folder), method_map=[("**.py", "python")], keywords=KEYWORDS)
    return {m[2] for m in found if isinstance(m[2], str) and m[2]}


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("source,catalog", CATALOGS, ids=["frontend", "backend"])
def test_every_message_is_translated(source, catalog):
    with open(catalog.with_suffix(".po"), "rb") as f:
        po = {m.id: m.string for m in read_po(f, locale="km") if m.id}
    missing = sorted(m for m in _source_messages(source) if not po.get(m))
    # machine codes (e.g. otp_required) are compared by the client and must stay untranslated
    missing = [m for m in missing if not re.fullmatch(r"[a-z0-9_]+", m)]
    assert not missing, f"untranslated in {catalog.name}.po: {missing[:10]}"


@pytest.mark.parametrize("catalog", [c for _, c in CATALOGS], ids=["frontend", "backend"])
def test_placeholders_match(catalog):
    with open(catalog.with_suffix(".po"), "rb") as f:
        wrong = [m.id for m in read_po(f, locale="km")
                 if m.id and m.string and _placeholders(m.id) != _placeholders(m.string)]
    assert not wrong, f"placeholders differ: {wrong[:10]}"


@pytest.mark.parametrize("catalog", [c for _, c in CATALOGS], ids=["frontend", "backend"])
def test_compiled_catalog_is_current(catalog):
    """The .mo the app loads must contain everything in the .po (run pybabel compile after editing)."""
    with open(catalog.with_suffix(".po"), "rb") as f:
        po = {m.id: m.string for m in read_po(f, locale="km") if m.id and m.string}
    with open(catalog.with_suffix(".mo"), "rb") as f:
        mo = {m.id: m.string for m in read_mo(f) if m.id}
    assert mo == po


def test_frontend_switches_language():
    from core import i18n
    from core.i18n import _
    assert _("Employee Directory") == "Employee Directory"
    i18n.set_language("km")
    assert _("Employee Directory") == "បញ្ជីបុគ្គលិក"
    assert _("not a catalog entry") == "not a catalog entry"
