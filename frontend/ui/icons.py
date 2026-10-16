"""Icon images rendered from the Windows Segoe icon font.

`icon("search", 16)` returns a CTkImage (light + dark variants) or None when no
icon font is available, so callers can always fall back to text-only widgets.
"""
import os
from functools import cache

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from . import theme as T

# Segoe MDL2 Assets / Segoe Fluent Icons code points
GLYPHS = {
    "dashboard": "\uE80A",
    "people": "\uE716",
    "person": "\uE77B",
    "add_person": "\uE8FA",
    "department": "\uE821",
    "clock": "\uE823",
    "leave": "\uE709",
    "payroll": "\uE8C7",
    "settings": "\uE713",
    "logout": "\uE7E8",
    "moon": "\uE708",
    "sun": "\uE706",
    "search": "\uE721",
    "view": "\uE890",
    "edit": "\uE70F",
    "delete": "\uE74D",
    "add": "\uE710",
    "download": "\uE896",
    "refresh": "\uE72C",
    "calendar": "\uE787",
    "bell": "\uEA8F",
    "check": "\uE73E",
    "close": "\uE711",
    "chevron_right": "\uE76C",
    "chevron_left": "\uE76B",
    "document": "\uE8A5",
    "print": "\uE749",
    "stopwatch": "\uE916",
    "bolt": "\uE945",
    "lock": "\uE72E",
    "shield": "\uE83D",
    "filter": "\uE71C",
    "info": "\uE946",
    "warning": "\uE7BA",
    "bank": "\uE825",
    "trend": "\uE9D9",
    "database": "\uE968",
    "history": "\uE81C",
    "mail": "\uE715",
    "play": "\uE768",
    "stop": "\uE71A",
    "location": "\uE707",
    "org": "\uE8F1",
    "medical": "\uE95E",
    "palette": "\uE790",
    "globe": "\uE909",
}

_FONT_FILES = ("SegoeIcons.ttf", "segmdl2.ttf")
_FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


@cache
def _pil_font(px: int):
    for name in _FONT_FILES:
        for path in (os.path.join(_FONT_DIR, name), name):
            try:
                return ImageFont.truetype(path, px)
            except OSError:
                continue
    return None


def available() -> bool:
    return _pil_font(16) is not None


def _render(glyph: str, size: int, color: str) -> Image.Image:
    scale = 2  # render at 2x so it stays crisp on HiDPI
    px = size * scale
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((px / 2, px / 2), glyph, font=_pil_font(px), fill=color, anchor="mm")
    return img


@cache
def icon(name: str, size: int = 16, color=T.TEXT_2):
    """Return a CTkImage for `name`, coloured with a hex or (light, dark) tuple."""
    glyph = GLYPHS.get(name)
    if glyph is None or not available():
        return None
    light, dark = (color, color) if isinstance(color, str) else color
    return ctk.CTkImage(
        light_image=_render(glyph, size, light),
        dark_image=_render(glyph, size, dark),
        size=(size, size),
    )


@cache
def logo_image(size: int = 40) -> Image.Image:
    """The 'M' mark: blue rounded square, white M, light-blue dot."""
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=60, fill="#2563EB")
    w = 20
    pts = [(72, 180), (72, 76), (128, 132), (184, 76), (184, 180)]
    d.line(pts, fill="white", width=w, joint="curve")
    for x, y in (pts[0], pts[-1], pts[1], pts[3]):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill="white")
    d.ellipse((112, 146, 144, 178), fill="#60A5FA")
    return img.resize((size * 2, size * 2), Image.LANCZOS)


def logo(size: int = 40) -> ctk.CTkImage:
    img = logo_image(size)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
