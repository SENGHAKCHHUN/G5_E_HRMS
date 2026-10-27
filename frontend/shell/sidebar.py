"""Left sidebar: brand, one button per screen, language, dark mode, logout."""
import tkinter as tk

import customtkinter as ctk

from core import i18n
from core.i18n import _
from core.state import state
from ui import theme as T
from ui import widgets as W
from ui.icons import icon, logo


class SidebarMixin:
    """Part of Shell (shell/__init__.py): builds the left sidebar."""

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=T.SIDEBAR_WIDTH, fg_color=T.SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        sb.pack_propagate(False)
        # thin line between sidebar and content (visible in light mode); packed first to span full height
        ctk.CTkFrame(sb, width=1, fg_color=T.SIDEBAR_BORDER, corner_radius=0).pack(side="right", fill="y")

        brand = W.transparent(sb)
        brand.pack(fill="x", padx=16, pady=(18, 22))
        ctk.CTkLabel(brand, text="", image=logo(38)).pack(side="left")
        txt = W.transparent(brand)
        txt.pack(side="left", padx=10)
        W.label(txt, "HRMS", size=16, weight="bold", color=T.SIDEBAR_TITLE).pack(anchor="w")
        W.label(txt, _("HR Management System"), size=11, color=T.SIDEBAR_MUTED).pack(anchor="w")

        self.nav_buttons = {}
        for key, text, icon_name, *_rest in self.nav:
            b = ctk.CTkButton(
                sb, text=_(text), anchor="w", height=40, corner_radius=T.RADIUS_BTN,
                font=T.font(13, "semibold"), fg_color="transparent", hover_color=T.SIDEBAR_HOVER,
                text_color=T.SIDEBAR_TEXT, image=icon(icon_name, 16, T.SIDEBAR_MUTED),
                compound="left", border_spacing=10, command=lambda k=key: self.navigate(k))
            b.pack(fill="x", padx=12, pady=2)
            b._icon_name = icon_name
            self.nav_buttons[key] = b

        bottom = W.transparent(sb)
        bottom.pack(side="bottom", fill="x", padx=12, pady=16)
        lang = ctk.CTkFrame(bottom, fg_color="transparent")
        lang.pack(fill="x", pady=(0, 8))
        self.lang_switch = W.segmented(lang, list(i18n.LANGUAGES.values()), command=self._pick_language)
        self.lang_switch.set(i18n.LANGUAGES[state.language])
        self.lang_switch.pack(fill="x")
        mode = ctk.CTkFrame(bottom, fg_color=T.SIDEBAR_HOVER, corner_radius=T.RADIUS_BTN, height=40)
        mode.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(mode, text="", image=icon("moon", 15, T.SIDEBAR_TEXT)).pack(side="left", padx=(12, 8))
        W.label(mode, _("Dark Mode"), size=13, color=T.SIDEBAR_TEXT).pack(side="left", pady=8)
        self.dark_var = tk.BooleanVar(value=ctk.get_appearance_mode() == "Dark")
        W.switch(mode, command=self.toggle_theme, variable=self.dark_var).pack(side="right", padx=8)

        ctk.CTkButton(bottom, text=_("Logout"), anchor="w", height=40, corner_radius=T.RADIUS_BTN,
                      font=T.font(13, "semibold"), fg_color="transparent",
                      hover_color=T.SIDEBAR_HOVER, text_color=T.SIDEBAR_DANGER,
                      image=icon("logout", 16, T.SIDEBAR_DANGER), compound="left",
                      border_spacing=10, command=self.logout).pack(fill="x")

    def _highlight(self, key):
        for k, b in self.nav_buttons.items():
            active = k == key
            b.configure(fg_color=T.PRIMARY if active else "transparent",
                        hover_color=T.PRIMARY_HOVER if active else T.SIDEBAR_HOVER,
                        text_color=T.WHITE if active else T.SIDEBAR_TEXT,
                        image=icon(b._icon_name, 16, T.WHITE if active else T.SIDEBAR_MUTED))
