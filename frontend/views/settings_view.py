"""Settings & System Configuration (Admin only)."""
import platform
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
import requests

from core import prefs, tasks
from core.api_client import api
from core.i18n import N_, _
from core.state import state
from logic import labels
from ui import theme as T
from ui import widgets as W

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
DAYS = list(labels.WEEKDAYS)
TIMEZONES = ["(UTC+07:00) Bangkok, Hanoi, Phnom Penh", "(UTC+08:00) Singapore, Kuala Lumpur",
             "(UTC+00:00) London, Dublin", "(UTC-05:00) Eastern Time (US & Canada)",
             "(UTC-08:00) Pacific Time (US & Canada)"]


def _shift_hours(start: str, end: str) -> float:
    try:
        diff = datetime.strptime(end, "%H:%M") - datetime.strptime(start, "%H:%M")
    except ValueError:
        return 8.0
    return max(0.0, diff.total_seconds() / 3600)


def _ping(url: str) -> float:
    started = time.perf_counter()
    requests.get(url.rstrip("/") + "/", timeout=2).raise_for_status()  # health check
    return (time.perf_counter() - started) * 1000


def _save_and_test(values: dict, to: str):
    saved = api.save_settings(values)
    api.send_test_email(to)
    return saved


class SettingsView(ctk.CTkFrame):
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

    # --------------------------------------------------------------- sections
    def _sec_general(self):
        b = self._section(_("Company & Workplace Profile"),
                          _("Used on payslip headers, reports and email"), "org")
        self._field(b, "company_name", _("Company Name"), 0, 0)
        self._field(b, "domain", _("Company Domain"), 0, 1)
        self._option(b, "timezone", _("Operational Timezone"), TIMEZONES, 1, 0, span=2)

        week = ctk.CTkFrame(b, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        week.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        top = W.transparent(week)
        top.pack(fill="x", padx=14, pady=(12, 8))
        W.label(top, _("Work Week"), size=13, weight="semibold").pack(side="left")
        hours = W.label(top, "", size=12, color=T.TEXT_2)
        hours.pack(side="right")
        days = W.transparent(week)
        days.pack(fill="x", padx=14, pady=(0, 14))
        W.grid_columns(days, 7, uniform="days")
        selected = set(self.values.get("work_week", []))
        per_day = _shift_hours(self.values.get("shift_start", "09:00"), self.values.get("shift_end", "18:00"))
        buttons = {}

        def paint():
            for d, btn in buttons.items():
                on = d in selected
                btn.configure(fg_color=T.PRIMARY if on else T.ELEVATED,
                              text_color=T.WHITE if on else T.TEXT_2,
                              hover_color=T.PRIMARY_HOVER if on else T.ELEVATED_HOVER)
            week = round(len(selected) * per_day, 1)
            hours.configure(text=_("{hours:g} scheduled hours per week").format(hours=week))

        def flip(d):
            selected.symmetric_difference_update({d})
            paint()

        for i, d in enumerate(DAYS):
            btn = ctk.CTkButton(days, text=labels.show(labels.WEEKDAYS, d), height=36, corner_radius=T.RADIUS_BTN,
                                font=T.font(13, "semibold"), command=lambda d=d: flip(d))
            btn.grid(row=0, column=i, sticky="ew", padx=3)
            buttons[d] = btn
        paint()
        self.getters["work_week"] = lambda: [d for d in DAYS if d in selected]

    def _sec_auth(self):
        b = self._section(_("Security & Session Policy"), _("Role-based access control and session length"),
                          "shield", right=_("RBAC Enforced"))
        self._option(b, "jwt_hours", _("Session Expiry (hours)"), ["1", "4", "8", "12", "24"], 0, 0)
        self._toggle_row(b, "enforce_mfa", _("Enforce 2FA for staff"),
                         _("Admin & HR must use an authenticator app"), 0, 1)

        W.label(b, _("Role Permissions Overview"), size=13, weight="semibold").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(14, 6))
        perms = W.DataTable(b, [
            {"key": "role", "title": _("Role"), "weight": 10,
             "render": lambda m, r: W.dot_text(m, labels.show(labels.ROLE, r["role"]), r["color"])},
            {"key": "emp", "title": _("Employees"), "weight": 12},
            {"key": "pay", "title": _("Payroll"), "weight": 12},
            {"key": "att", "title": _("Attendance"), "weight": 12},
            {"key": "sys", "title": _("Settings"), "weight": 10},
        ], row_height=42)
        perms.grid(row=2, column=0, columnspan=2, sticky="ew")
        perms.set_rows([
            {"role": "Admin", "color": T.DANGER, "emp": _("Full (Read/Write)"), "pay": _("Full (Pay)"),
             "att": _("Full (Override)"), "sys": _("Full")},
            {"role": "HR Manager", "color": T.PRIMARY, "emp": _("Full (Read/Write)"), "pay": _("Calculate & Run"),
             "att": _("Approve / Log"), "sys": _("None")},
            {"role": "Employee", "color": T.SUCCESS, "emp": _("Own profile"), "pay": _("Own payslips"),
             "att": _("Own clock in/out"), "sys": _("None")},
        ])

        u = self._section(_("User Accounts"), _("Reset a forgotten password or a lost authenticator"), "person")
        self.users = W.DataTable(u, [
            {"key": "username", "title": _("Username"), "weight": 10,
             "render": lambda m, r: W.label(m, r["username"], size=13, weight="semibold", mono=True)},
            {"key": "role", "title": _("Role"), "weight": 9,
             "render": lambda m, r: W.badge(m, labels.show(labels.ROLE, r["role"]),
                                            {"Admin": "danger", "HR Manager": "info"}.get(r["role"], "success"))},
            {"key": "employee", "title": _("Linked Employee"), "weight": 15},
            {"key": "security", "title": _("Security"), "weight": 9, "render": self._security_cell},
            {"key": "actions", "title": _("Actions"), "weight": 15, "anchor": "e", "render": self._user_actions},
        ], row_height=48)
        self.users.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.user_pager = W.Paginator(self.users.footer, self._show_users, page_size=8)
        self.user_pager.pack(fill="x", pady=(6, 0))
        self.all_users: list[dict] = []
        self._reload_users()

    def _show_users(self):
        self.users.set_rows(self.user_pager.slice(self.all_users))

    def _reload_users(self):
        self.users.set_loading()

        def show(users):
            self.all_users = users
            if self.users.winfo_exists():
                self._show_users()
        tasks.run(self.users, api.get_users, on_done=show)

    @staticmethod
    def _security_cell(m, r):
        box = W.transparent(m)
        if r.get("totp_enabled"):
            W.badge(box, "2FA", "success").pack(side="left", padx=(0, 4))
        if r.get("must_change_password"):
            W.badge(box, _("Temp"), "warning").pack(side="left")
        if not box.winfo_children():
            W.label(box, _("Password"), size=12, color=T.TEXT_2).pack(side="left")
        return box

    def _user_actions(self, m, r):
        box = W.transparent(m)
        W.button(box, _("Reset Password"), "secondary", command=lambda: self._reset_password(r),
                 height=28, size=11).pack(side="left", padx=2)
        if r.get("totp_enabled"):
            W.button(box, _("Reset 2FA"), "danger_soft", command=lambda: self._reset_2fa(r),
                     height=28, size=11).pack(side="left", padx=2)
        return box

    def _reset_password(self, r):
        if W.confirm(self, _("Reset Password"),
                     _("Create a one-time temporary password for '{user}'?\nTheir current password stops working "
                       "and they must choose a new one at next sign-in.").format(user=r["username"]),
                     ok_text=_("Reset"), kind="primary"):
            tasks.run(self, api.reset_password, r["id"], on_done=self._show_temporary_password)

    def _show_temporary_password(self, res):
        self._reload_users()
        dlg = W.Modal(self, _("Temporary Password"), _("For {user}").format(user=res["username"]), width=460,
                      height=300, scroll=False)
        W.label(dlg.body, _("Give this password to the user. It works once; they will be asked to set "
                            "their own password when they sign in."), size=12, color=T.TEXT_2,
                wraplength=400, justify="left").pack(anchor="w", padx=16, pady=(8, 10))
        W.label(dlg.body, res["temporary_password"], size=20, weight="bold", mono=True,
                color=T.PRIMARY).pack(anchor="w", padx=16)

        def copy():
            dlg.clipboard_clear()
            dlg.clipboard_append(res["temporary_password"])
            W.toast(dlg, _("Copied"))
        dlg.add_button(_("Done"), "primary", dlg.destroy)
        dlg.add_button(_("Copy"), "secondary", copy, "document")

    def _reset_2fa(self, r):
        if not W.confirm(self, _("Reset Two-Factor Authentication"),
                         _("Turn off 2FA for '{user}' (for example after losing their phone)? "
                           "They can set it up again from their user menu.").format(user=r["username"]),
                         ok_text=_("Reset 2FA")):
            return

        def done(_result):
            self._reload_users()
            W.toast(self, _("2FA reset for {user}").format(user=r["username"]), "warning")
        tasks.run(self, api.reset_2fa, r["id"], on_done=done)

    def _sec_attendance(self):
        b = self._section(_("Attendance Policies"), _("Shift schedule, grace period and overtime rules"), "clock")
        self._field(b, "shift_start", _("Shift Start (HH:MM)"), 0, 0)
        self._field(b, "shift_end", _("Shift End (HH:MM)"), 0, 1)
        self._field(b, "grace_minutes", _("Late Grace Period (minutes)"), 1, 0, cast=int)
        self._field(b, "overtime_after", _("Overtime Counted After (HH:MM)"), 1, 1)

        r = self._section(_("Check-In Rules"), _("Enforced by the server, using the server's clock"), "lock",
                          right=_("Server Enforced"))
        self._field(r, "checkin_open", _("Check-in Opens (HH:MM)"), 0, 0)
        self._field(r, "checkin_close", _("Check-in Closes (HH:MM)"), 0, 1)
        self._toggle_row(r, "restrict_network", _("Office network only"),
                         _("Clock in/out only from the networks below"), 1, 0)
        self._toggle_row(r, "remote_exempt", _("Remote staff exempt"),
                         _("Work mode 'Remote' may clock in from anywhere"), 1, 1)
        self._field(r, "office_networks", _("Office Networks (IP addresses or ranges, comma-separated)"), 2, 0,
                    span=2)
        W.label(r, _("Example: 192.168.1.0/24, 10.0.0.0/8. Forgotten or off-site punches are fixed by HR with "
                     "Manual Log Entry."), size=11, color=T.TEXT_2, wraplength=700, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w")

    def _sec_payroll(self):
        b = self._section(_("Payroll & Tax Configuration"), _("Rates applied when payroll is generated"), "payroll")
        self._field(b, "tax_rate", _("Income Tax Rate (%)"), 0, 0, cast=float)
        self._field(b, "pension_rate", _("Pension Contribution (%)"), 0, 1, cast=float)
        self._field(b, "pay_day", _("Monthly Pay Day"), 1, 0, cast=int)
        self._option(b, "currency", _("Currency"), ["USD", "KHR", "EUR", "SGD"], 1, 1)

    def _sec_backend(self):
        b = self._section(_("Backend & Local Database"), _("FastAPI service and SQLAlchemy storage"), "database")
        box = W.transparent(b)
        box.grid(row=0, column=0, columnspan=2, sticky="ew")
        W.label(box, _("Backend API Endpoint URL"), size=12, weight="semibold", color=T.TEXT_2).pack(
            anchor="w", pady=(0, 4))
        row = W.transparent(box)
        row.pack(fill="x")
        e = W.entry(row)
        e.pack(side="left", fill="x", expand=True)
        e.insert(0, self.values.get("api_url", api.base_url))
        self.getters["api_url"] = lambda: e.get().strip()
        status = W.badge(box, _("Checking..."), "neutral")

        def show_status(text, kind):
            if status.winfo_exists():
                status.configure(text=text, fg_color=T.BADGE[kind][0], text_color=T.BADGE[kind][1])

        def ping():
            tasks.run(status, _ping, e.get().strip(),
                      on_done=lambda ms: show_status("● " + _("Reachable ({ms} ms)").format(ms=round(ms)), "success"),
                      on_error=lambda _err: show_status("● " + _("Unreachable - is the backend running?"), "danger"))

        W.button(row, _("Test Ping"), "secondary", "bolt", ping, height=36).pack(side="left", padx=(8, 0))
        status.pack(anchor="w", pady=(8, 0))
        tasks.run(status, api.health, on_done=lambda res: show_status(res[1], "success" if res[0] else "warning"))

        cards = W.transparent(b)
        cards.grid(row=1, column=0, columnspan=2, sticky="ew")
        cards.grid_columnconfigure((0, 1), weight=1, uniform="db")
        W.label(cards, _("Loading..."), color=T.TEXT_3).grid(row=0, column=0, pady=20)

        def show_info(info):
            for w in cards.winfo_children():
                w.destroy()
            size = f"{info['size_mb']} MB" if info["size_mb"] is not None else "n/a"
            items = [(_("Database Engine"), f"{info['driver'].capitalize()} (SQLAlchemy ORM)", info["url"]),
                     (_("Database Contents"), size,
                      _("{employees} employees · {attendance} attendance rows · {payroll} payroll lines").format(
                          employees=info["employees"], attendance=f"{info['attendance_rows']:,}",
                          payroll=f"{info['payroll_rows']:,}"))]
            for i, (title, value, sub) in enumerate(items):
                w = ctk.CTkFrame(cards, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
                w.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0), pady=(14, 0))
                W.micro(w, title).pack(anchor="w", padx=14, pady=(12, 2))
                W.label(w, value, size=14, weight="semibold").pack(anchor="w", padx=14)
                W.label(w, sub, size=11, color=T.TEXT_2, wraplength=330, justify="left").pack(
                    anchor="w", padx=14, pady=(0, 12))
        tasks.run(cards, api.database_info, on_done=show_info)

        foot = W.transparent(b)
        foot.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        W.label(foot, _("Set HRMS_DATABASE_URL to switch to PostgreSQL / MySQL."), size=12,
                color=T.TEXT_2).pack(side="left")
        W.button(foot, _("Download Backup"), "secondary", "download", self._backup, height=34, size=12).pack(
            side="right")

    def _backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite database", "*.db")],
                                            initialfile=f"hrms_backup_{datetime.now():%Y%m%d_%H%M}.db")
        if not path:
            return

        def write(data):
            with open(path, "wb") as f:
                f.write(data)
            W.toast(self, _("Backup saved ({size} MB)").format(size=f"{len(data) / 1e6:.1f}"))
        tasks.run(self, api.download_backup, on_done=write)

    def _sec_email(self):
        configured = self.values.get("smtp_host") and self.values.get("smtp_from")
        b = self._section(_("Email (SMTP)"), _("Used to email payslips and leave decisions"), "mail",
                          right=_("Configured") if configured else None)
        self._field(b, "smtp_host", _("SMTP Server (e.g. smtp.gmail.com)"), 0, 0)
        self._field(b, "smtp_port", _("Port (587 = STARTTLS, 465 = SSL)"), 0, 1, cast=int)
        self._field(b, "smtp_user", _("Username (leave blank if not required)"), 1, 0)
        label = _("Password (saved - leave blank to keep)") if self.values.get("smtp_password_set") else _("Password")
        pw = self._field(b, "smtp_password", label, 1, 1)
        pw.configure(show="*")
        self._field(b, "smtp_from", _("Sender Address (From)"), 2, 0, span=2)
        self._toggle_row(b, "smtp_tls", _("Use STARTTLS"), _("Encrypt the connection (port 587)"), 3, 0)
        self._toggle_row(b, "email_notifications", _("Leave notifications"),
                         _("Email employees when leave is approved/rejected"), 3, 1)

        t = ctk.CTkFrame(b, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        t.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        W.label(t, _("Send a test email to:"), size=12, color=T.TEXT_2).pack(side="left", padx=(14, 8), pady=12)
        to = W.entry(t, _("name@example.com"), width=240)
        to.pack(side="left")

        def send_test():
            self._collect()  # test with what is on screen
            address = to.get().strip()
            tasks.run(self, _save_and_test, dict(self.values), address,
                      on_done=lambda saved: self._saved(saved, _("Test email sent to {to}").format(to=address)))
        W.button(t, _("Save & Send Test"), "primary", "mail", send_test, height=34, size=12).pack(side="left", padx=10)

    def _sec_appearance(self):
        b = self._section(_("Appearance & Theme Preferences"), _("Theme, scaling and accent colour on this computer"),
                          "palette")
        modes = {"Dark": _("Dark"), "Light": _("Light"), "System": _("System")}
        W.label(b, _("Theme Mode"), size=12, weight="semibold", color=T.TEXT_2).grid(row=0, column=0, sticky="w")
        theme = W.segmented(b, list(modes.values()), command=lambda v: self.app.set_theme(
            next(k for k, shown in modes.items() if shown == v).lower()))
        theme.set(modes.get(ctk.get_appearance_mode(), modes["Dark"]))
        theme.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        W.label(b, _("UI Scaling"), size=12, weight="semibold", color=T.TEXT_2).grid(
            row=0, column=1, sticky="w", padx=(8, 0))

        def set_scale(v):
            state.scaling = int(v[:-1]) / 100
            ctk.set_widget_scaling(state.scaling)
            prefs.save(scaling=state.scaling)
        scale = W.segmented(b, ["90%", "100%", "110%", "125%"], command=set_scale)
        scale.set(f"{round(state.scaling * 100)}%")
        scale.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))

        W.label(b, _("Accent colour"), size=12, weight="semibold", color=T.TEXT_2).grid(
            row=2, column=0, sticky="w", pady=(16, 4))
        sw = W.transparent(b)
        sw.grid(row=3, column=0, columnspan=2, sticky="w")
        for name, (primary, *_rest) in T.ACCENTS.items():
            chosen = name == state.accent
            ctk.CTkButton(sw, text="✓" if chosen else "", width=34, height=34, corner_radius=17,
                          fg_color=primary, hover_color=primary, text_color="#FFFFFF",
                          border_width=3 if chosen else 0, border_color=T.TEXT,
                          font=T.font(14, "bold"), command=lambda n=name: self._set_accent(n)).pack(
                side="left", padx=(0, 10))
        W.label(sw, _("Saved on this computer"), size=12, color=T.TEXT_2).pack(side="left", padx=6)

    def _set_accent(self, name):
        state.accent = name
        prefs.save(accent=name)
        T.apply_accent(name)
        self.app.app.rebuild("settings")  # every screen picks up the new colour

    def _sec_audit(self):
        b = self._section(_("Audit & Security Logs"), _("Privileged actions recorded by the backend"), "history")
        table = W.DataTable(b, [
            {"key": "when", "title": _("Timestamp"), "weight": 12,
             "render": lambda m, r: W.label(m, r["when"], size=12, mono=True)},
            {"key": "user", "title": _("User"), "weight": 7,
             "render": lambda m, r: W.label(m, r["user"], size=12, weight="semibold")},
            {"key": "action", "title": _("Action"), "weight": 8,
             "render": lambda m, r: W.badge(m, r["action"], "info", dot=False)},
            {"key": "detail", "title": _("Detail"), "weight": 26},
        ], row_height=42, empty_text=_("No audit entries yet"))
        table.grid(row=0, column=0, columnspan=2, sticky="ew")

        def show(page):
            table.set_rows(page.rows)
            pager.update(page.total, len(page.rows))

        def load():
            table.set_loading()
            tasks.run(table, api.audit_page, limit=pager.limit, offset=pager.offset, on_done=show)
        pager = W.Paginator(table.footer, load, page_size=12)
        pager.pack(fill="x", pady=(6, 0))
        load()

