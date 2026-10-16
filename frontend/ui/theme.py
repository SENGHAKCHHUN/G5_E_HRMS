"""Design tokens for the HRMS desktop UI (Slate Desktop System).

Every colour is a (light, dark) tuple so CustomTkinter switches automatically
when the appearance mode changes.
"""
import sys
import tkinter.font as tkfont
from functools import cache
from pathlib import Path

import customtkinter as ctk

from core import i18n

# ---------------------------------------------------------------- colours ---
PRIMARY = ("#2563EB", "#3B82F6")
PRIMARY_HOVER = ("#1D4ED8", "#2563EB")
PRIMARY_SOFT = ("#DBEAFE", "#1A2D52")      # tinted primary background
SEG_SELECTED = ("#BFDBFE", "#3B82F6")      # selected segment (light mode keeps dark text readable)
SEG_SELECTED_HOVER = ("#93C5FD", "#2563EB")

# accent colour themes: name -> (primary, hover, soft, segment selected, segment hover)
ACCENTS = {
    "Blue": (("#2563EB", "#3B82F6"), ("#1D4ED8", "#2563EB"), ("#DBEAFE", "#1A2D52"),
             ("#BFDBFE", "#3B82F6"), ("#93C5FD", "#2563EB")),
    "Teal": (("#0F766E", "#14B8A6"), ("#115E59", "#0D9488"), ("#CCFBF1", "#0E3B3A"),
             ("#99F6E4", "#14B8A6"), ("#5EEAD4", "#0D9488")),
    "Emerald": (("#047857", "#10B981"), ("#065F46", "#059669"), ("#D1FAE5", "#0F3B2A"),
                ("#A7F3D0", "#10B981"), ("#6EE7B7", "#059669")),
    "Violet": (("#6D28D9", "#8B5CF6"), ("#5B21B6", "#7C3AED"), ("#EDE9FE", "#2A1F52"),
               ("#DDD6FE", "#8B5CF6"), ("#C4B5FD", "#7C3AED")),
}


def apply_accent(name: str):
    """Switch the accent colour. Widgets created afterwards use the new colours."""
    global PRIMARY, PRIMARY_HOVER, PRIMARY_SOFT, SEG_SELECTED, SEG_SELECTED_HOVER
    PRIMARY, PRIMARY_HOVER, PRIMARY_SOFT, SEG_SELECTED, SEG_SELECTED_HOVER = ACCENTS.get(name, ACCENTS["Blue"])
TEAL = ("#0D9488", "#14B8A6")
SUCCESS = ("#16A34A", "#22C55E")
SUCCESS_HOVER = ("#15803D", "#16A34A")
WARNING = ("#D97706", "#F59E0B")
DANGER = ("#DC2626", "#EF4444")
DANGER_HOVER = ("#B91C1C", "#DC2626")

BG = ("#F1F5F9", "#0B1120")                # app canvas
SURFACE = ("#FFFFFF", "#131D30")           # cards / frames
SURFACE_ALT = ("#F8FAFC", "#0E1728")       # zebra rows, nested wells
INPUT = ("#F8FAFC", "#0A1222")             # recessed inputs
ELEVATED = ("#E2E8F0", "#22304A")          # secondary buttons, chips
ELEVATED_HOVER = ("#CBD5E1", "#2D3E5C")
BORDER = ("#E2E8F0", "#1F2C44")
ROW_HOVER = ("#EFF6FF", "#17284A")

SIDEBAR = ("#FFFFFF", "#0D1526")           # white in light mode, navy in dark mode
SIDEBAR_HOVER = ("#F1F5F9", "#1A2540")
SIDEBAR_TEXT = ("#334155", "#CBD5E1")
SIDEBAR_MUTED = ("#64748B", "#94A3B8")
SIDEBAR_TITLE = ("#0F172A", "#F8FAFC")
SIDEBAR_BORDER = ("#E2E8F0", "#0D1526")    # divider next to the content (invisible in dark mode)
SIDEBAR_DANGER = ("#DC2626", "#F87171")    # Logout

TEXT = ("#0F172A", "#F1F5F9")
TEXT_2 = ("#475569", "#94A3B8")
TEXT_3 = ("#94A3B8", "#64748B")
WHITE = ("#FFFFFF", "#FFFFFF")

# badge palettes: kind -> (background, foreground)
BADGE = {
    "success": (("#DCFCE7", "#0F3B2A"), ("#15803D", "#4ADE80")),
    "warning": (("#FEF3C7", "#3D2E0F"), ("#B45309", "#FBBF24")),
    "danger": (("#FEE2E2", "#45161B"), ("#B91C1C", "#F87171")),
    "info": (("#DBEAFE", "#172E57"), ("#1D4ED8", "#93C5FD")),
    "neutral": (("#F1F5F9", "#26334A"), ("#475569", "#CBD5E1")),
    "teal": (("#CCFBF1", "#0E3B3A"), ("#0F766E", "#5EEAD4")),
}

# categorical colours for departments / charts (light, dark)
CATEGORY = [
    ("#2563EB", "#3B82F6"),
    ("#059669", "#34D399"),
    ("#7C3AED", "#A78BFA"),
    ("#D97706", "#FBBF24"),
    ("#DB2777", "#F472B6"),
    ("#0891B2", "#22D3EE"),
]

AVATAR_COLORS = [
    ("#3B82F6", "#3B82F6"), ("#475569", "#334155"), ("#0EA5E9", "#0284C7"),
    ("#10B981", "#059669"), ("#8B5CF6", "#7C3AED"), ("#EF4444", "#B91C1C"),
    ("#F59E0B", "#D97706"),
]

# ---------------------------------------------------------------- metrics ---
RADIUS_CARD = 10
RADIUS_BTN = 8
RADIUS_INPUT = 8
PAD = 16          # outer page padding / card padding
GAP = 16          # gutter between cards
SIDEBAR_WIDTH = 230


def mode_index() -> int:
    """0 for light, 1 for dark – handy for non-CTk widgets (matplotlib)."""
    return 1 if ctk.get_appearance_mode() == "Dark" else 0


def pick(color):
    """Resolve a (light, dark) tuple to the hex for the current mode."""
    if isinstance(color, (tuple, list)):
        return color[mode_index()]
    return color


# ------------------------------------------------------------------ fonts ---
# The UI uses the bundled "HRMS Sans" in both languages: Noto Sans (Latin) and Noto Sans Khmer merged
# into one family (scripts/build_fonts.py, SIL Open Font License, see assets/fonts/OFL.txt). Tk draws a
# label with one font, so a Latin-only or Khmer-only font would leave the other script to whatever
# font Windows substitutes, in a mismatched style.
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
UI_FONT = "HRMS Sans"
UI_SEMIBOLD = "HRMS Sans SemiBold"
KHMER_FALLBACK = "Khmer UI"  # ships with Windows; used only if the bundled fonts could not be loaded


def load_bundled_fonts() -> None:
    """Make the bundled fonts usable by this app only (nothing is installed). Call before the window opens."""
    for path in sorted(FONT_DIR.glob("*.ttf")):
        if sys.platform == "win32":  # enumerable, so tkfont.families() lists it
            ctk.FontManager.windows_load_font(str(path), private=True, enumerable=True)
        else:
            ctk.FontManager.load_font(str(path))


@cache
def _families():
    return set(tkfont.families())


def khmer_family() -> str:
    """A family that can show Khmer (e.g. the language names in a menu)."""
    return UI_FONT if UI_FONT in _families() else KHMER_FALLBACK


def _family(weight: str) -> tuple[str, str]:
    fams = _families()
    bold = "bold" if weight in ("bold", "semibold") else "normal"
    if UI_FONT in fams:
        if weight == "semibold" and UI_SEMIBOLD in fams:
            return UI_SEMIBOLD, "normal"
        return UI_FONT, bold
    # bundled fonts missing: the best system font for the current language
    if i18n.is_khmer() and KHMER_FALLBACK in fams:
        return KHMER_FALLBACK, bold
    if weight == "semibold" and "Segoe UI Semibold" in fams:
        return "Segoe UI Semibold", "normal"
    return ("Segoe UI" if "Segoe UI" in fams else "Helvetica"), bold


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """weight: normal | semibold | bold (the family follows the current language)."""
    return _font(size, weight, i18n.language())


@cache
def _font(size: int, weight: str, _language: str) -> ctk.CTkFont:
    family, w = _family(weight)
    if _language == "km" and size <= 12:
        size += 1  # Khmer letters look smaller than Latin ones at the same size
    return ctk.CTkFont(family=family, size=size, weight=w)


def menu_font(size: int = 10) -> tuple[str, int]:
    """Font for plain tk menus (they cannot use CTkFont)."""
    return _family("normal")[0], size


@cache
def mono(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    fams = _families()
    family = next((f for f in ("JetBrains Mono", "Consolas", "Courier New") if f in fams), "Courier")
    return ctk.CTkFont(family=family, size=size, weight="bold" if weight != "normal" else "normal")
