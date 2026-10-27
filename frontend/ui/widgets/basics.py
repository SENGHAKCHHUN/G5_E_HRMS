"""Small building blocks: text, cards, buttons, badges, tags, avatars and icon tiles."""
import customtkinter as ctk

from .. import theme as T
from ..icons import icon


def label(master, text="", size=13, weight="normal", color=T.TEXT, mono=False, **kw):
    f = T.mono(size, weight) if mono else T.font(size, weight)
    kw.setdefault("anchor", "w")
    return ctk.CTkLabel(master, text=text, font=f, text_color=color, **kw)


def micro(master, text, color=T.TEXT_2, **kw):
    """Uppercase micro-label (label-sm)."""
    return label(master, text.upper(), size=11, weight="semibold", color=color, **kw)


def card(master, fg=T.SURFACE, border=True, radius=T.RADIUS_CARD, **kw):
    return ctk.CTkFrame(master, fg_color=fg, corner_radius=radius,
                        border_width=1 if border else 0, border_color=T.BORDER, **kw)


def transparent(master, **kw):
    # empty CTkFrames request 200x200 by default; collapse them instead
    kw.setdefault("width", 1)
    kw.setdefault("height", 1)
    return ctk.CTkFrame(master, fg_color="transparent", corner_radius=0, **kw)


def divider(master, vertical=False):
    if vertical:
        return ctk.CTkFrame(master, width=1, fg_color=T.BORDER, corner_radius=0)
    return ctk.CTkFrame(master, height=1, fg_color=T.BORDER, corner_radius=0)


def _btn_style(kind):
    # built on each call so a changed accent colour (theme.apply_accent) is picked up
    return {
        "primary": dict(fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOVER, text_color=T.WHITE),
        "secondary": dict(fg_color=T.ELEVATED, hover_color=T.ELEVATED_HOVER, text_color=T.TEXT),
        "success": dict(fg_color=T.SUCCESS, hover_color=T.SUCCESS_HOVER, text_color=T.WHITE),
        "danger": dict(fg_color=T.DANGER, hover_color=T.DANGER_HOVER, text_color=T.WHITE),
        "danger_soft": dict(fg_color=T.BADGE["danger"][0], hover_color=T.DANGER,
                            text_color=T.BADGE["danger"][1]),
        "ghost": dict(fg_color="transparent", hover_color=T.ELEVATED, text_color=T.TEXT_2),
        "link": dict(fg_color="transparent", hover_color=T.SURFACE_ALT, text_color=T.PRIMARY),
        "soft": dict(fg_color=T.PRIMARY_SOFT, hover_color=T.ELEVATED_HOVER, text_color=T.PRIMARY),
    }[kind]


def _icon_color(kind):
    return {"primary": T.WHITE, "success": T.WHITE, "danger": T.WHITE, "secondary": T.TEXT,
            "danger_soft": T.BADGE["danger"][1], "ghost": T.TEXT_2, "link": T.PRIMARY,
            "soft": T.PRIMARY}[kind]


def button(master, text="", kind="primary", icon_name=None, command=None, height=36,
           width=None, size=13, **kw):
    style = _btn_style(kind)
    style.update(kw)
    img = icon(icon_name, 14, _icon_color(kind)) if icon_name else None
    if width is None:
        width = 36 if not text else 0
    return ctk.CTkButton(master, text=text, image=img, compound="left", command=command,
                         height=height, width=width, corner_radius=T.RADIUS_BTN,
                         font=T.font(size, "semibold"), border_spacing=6, **style)


def icon_button(master, icon_name, command=None, kind="secondary", size=32, fallback="•"):
    img = icon(icon_name, 15, _icon_color(kind))
    style = _btn_style(kind)
    return ctk.CTkButton(master, text="" if img else fallback, image=img, command=command,
                         width=size, height=size, corner_radius=T.RADIUS_BTN,
                         font=T.font(13), border_spacing=0, **style)


def badge(master, text, kind="neutral", dot=True, size=11):
    bg, fg = T.BADGE[kind]
    return ctk.CTkLabel(master, text=("● " if dot else "") + text, fg_color=bg, text_color=fg,
                        corner_radius=6, font=T.font(size, "semibold"), height=22, padx=8)


def tag(master, text, kind="neutral", mono=False):
    bg, fg = T.BADGE[kind]
    return ctk.CTkLabel(master, text=text, fg_color=bg, text_color=fg, corner_radius=6,
                        font=T.mono(12) if mono else T.font(11, "semibold"), height=24, padx=8)


def avatar(master, first="", last="", size=34, color=None, text=None):
    initials = text or ((first[:1] + last[:1]).upper() or "?")
    if color is None:
        color = T.AVATAR_COLORS[(sum(map(ord, first + last))) % len(T.AVATAR_COLORS)]
    return ctk.CTkLabel(master, text=initials, width=size, height=size, fg_color=color,
                        corner_radius=8, text_color=T.WHITE, font=T.font(max(10, size // 3), "bold"))


def icon_tile(master, icon_name, kind="info", size=40, icon_size=18):
    bg, fg = T.BADGE[kind]
    img = icon(icon_name, icon_size, fg)
    return ctk.CTkLabel(master, text="" if img else "■", image=img, width=size, height=size,
                        fg_color=bg, text_color=fg, corner_radius=8)
