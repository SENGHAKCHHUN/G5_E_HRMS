"""Settings & System Configuration (Admin only)."""
import platform
import tkinter as tk

import customtkinter as ctk

from core import tasks
from core.api_client import api
from core.i18n import N_, _
from core.state import state
from ui import theme as T
from ui import widgets as W
from views.settings.accounts import AccountSection
from views.settings.general import GeneralSections
from views.settings.policies import PolicySections
from views.settings.system import SystemSections

DOMAINS = [
    ("general", N_("General & Company Info"), "org"),
    ("auth", N_("Authentication & Users"), "shield"),
    ("attendance", N_("Attendance & Policies"), "clock"),
    ("payroll", N_("Payroll & Tax Config"), "payroll"),
    ("email", N_("Email (SMTP)"), "mail"),
    ("backend", N_("Backend & Database"), "database"),
    ("appearance", N_("Appearance & Theme"), "palette"),
    ("audit", N_("Audit & Security Logs"), "history"),
]


class SettingsView(GeneralSections, AccountSection, PolicySections, SystemSections, ctk.CTkFrame):
    """The frame (domain list, Save / Discard, field helpers). Each domain's section is built by a part
    in views/settings/: general.py, accounts.py, policies.py, system.py."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.values = dict(state.settings)
        self.getters = {}
        self.domain = "general"

        header = W.PageHeader(self, _("Settings & System Configuration"),
                              _("Company preferences, security policy, email and the local database"),
                              icon_name="settings")
        header.pack(fill="x")
        header.add_action(_("Discard"), "secondary", "refresh", self.discard)
        header.add_action(_("Save Changes"), "primary", "check", self.save)

        body = W.transparent(self)
        body.pack(fill="both", expand=True, pady=(T.GAP, 0))
        body.grid_columnconfigure(0, weight=9, uniform="s")
        body.grid_columnconfigure(1, weight=24, uniform="s")

        left = W.transparent(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        nav = W.card(left)
        nav.pack(fill="x")
        W.micro(nav, _("Configuration Domains")).pack(anchor="w", padx=16, pady=(16, 8))
        self.nav_buttons = {}
        for key, text, ic in DOMAINS:
            b = W.button(nav, _(text), "ghost", ic, lambda k=key: self.show(k), height=38, size=13, anchor="w")
            b.pack(fill="x", padx=10, pady=1)
            self.nav_buttons[key] = (b, ic)
        ctk.CTkFrame(nav, height=10, fg_color="transparent").pack()

        rt = W.card(left)
        rt.pack(fill="x", pady=(T.GAP, 0))
        top = W.transparent(rt)
        top.pack(fill="x", padx=16, pady=(14, 6))
        W.micro(top, _("Desktop Runtime")).pack(side="left")
        ctk.CTkLabel(top, text="●", text_color=T.SUCCESS, font=T.font(12)).pack(side="right")
        well = ctk.CTkFrame(rt, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        well.pack(fill="x", padx=12, pady=(0, 14))
        for k, v in [(_("Framework"), f"CustomTkinter {ctk.__version__}"),
                     (_("Interpreter"), f"Python {platform.python_version()}"),
                     (_("Platform"), f"{platform.system()} {platform.release()}"),
                     (_("Backend"), api.base_url.replace("http://", ""))]:
            row = W.transparent(well)
            row.pack(fill="x", padx=12, pady=3)
            W.label(row, k + ":", size=12, color=T.TEXT_2).pack(side="left")
            W.label(row, v, size=12, weight="semibold").pack(side="right")

        self.content = W.transparent(body)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.show("general")

    # -------------------------------------------------------------- framework
    def show(self, key):
        self._collect()
        self.domain = key
        for k, (b, ic) in self.nav_buttons.items():
            active = k == key
            b.configure(fg_color=T.PRIMARY_SOFT if active else "transparent",
                        text_color=T.PRIMARY if active else T.TEXT_2,
                        image=W.icon(ic, 14, T.PRIMARY if active else T.TEXT_2))
        for w in self.content.winfo_children():
            w.destroy()
        self.getters = {}
        getattr(self, f"_sec_{key}")()

    def _collect(self):
        for k, getter in self.getters.items():
            self.values[k] = getter()

    def _saved(self, saved: dict, message: str | None = None):
        self.values = dict(saved)
        state.settings = dict(saved)  # currency, work week ... used by the other screens
        self.app.invalidate("dashboard", "attendance", "payroll", "employees", "departments", "leave")
        W.toast(self, message or _("Settings saved"))

    def save(self):
        self._collect()
        tasks.run(self, api.save_settings, dict(self.values), on_done=self._saved)

    def discard(self):
        def reset(settings):
            self.values = dict(settings)
            self.getters = {}
            self.show(self.domain)
            W.toast(self, _("Unsaved changes discarded"), "info")
        tasks.run(self, api.get_settings, on_done=reset)

    def _section(self, title, subtitle, icon_name, right=None):
        c = W.card(self.content)
        c.pack(fill="x", pady=(0, T.GAP))
        head = W.transparent(c)
        head.pack(fill="x", padx=18, pady=(16, 10))
        W.icon_tile(head, icon_name, "info", size=40, icon_size=18).pack(side="left")
        txt = W.transparent(head)
        txt.pack(side="left", padx=12)
        W.label(txt, title, size=16, weight="semibold").pack(anchor="w")
        W.label(txt, subtitle, size=12, color=T.TEXT_2).pack(anchor="w")
        if right:
            W.badge(head, right, "success").pack(side="right")
        body = W.transparent(c)
        body.pack(fill="x", padx=18, pady=(0, 18))
        body.grid_columnconfigure((0, 1), weight=1, uniform="f")
        return body

    def _field(self, body, key, text, row, col, span=1, cast=str):
        box = W.transparent(body)
        box.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=6)
        W.label(box, text, size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w", pady=(0, 4))
        e = W.entry(box)
        e.pack(fill="x")
        e.insert(0, str(self.values.get(key, "")))

        def get():
            try:
                return cast(e.get().strip())
            except ValueError:
                return self.values.get(key)
        self.getters[key] = get
        return e

    def _option(self, body, key, text, values, row, col, span=1):
        box = W.transparent(body)
        box.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=6)
        W.label(box, text, size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w", pady=(0, 4))
        cur = str(self.values.get(key, values[0]))
        var = tk.StringVar(value=cur if cur in values else values[0])
        W.option_menu(box, values, variable=var).pack(fill="x")
        self.getters[key] = var.get
        return var

    def _toggle_row(self, body, key, title, subtitle, row, col):
        box = ctk.CTkFrame(body, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        box.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=6)
        txt = W.transparent(box)
        txt.pack(side="left", padx=14, pady=10)
        W.label(txt, title, size=13, weight="semibold").pack(anchor="w")
        W.label(txt, subtitle, size=11, color=T.TEXT_2, wraplength=260, justify="left").pack(anchor="w")
        var = tk.BooleanVar(value=bool(self.values.get(key, False)))
        W.switch(box, variable=var).pack(side="right", padx=12)
        self.getters[key] = var.get
