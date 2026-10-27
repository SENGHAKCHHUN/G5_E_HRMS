"""Settings sections: backend & database, email (SMTP), audit log."""
import time
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
import requests

from core import tasks
from core.api_client import api
from core.i18n import _
from ui import theme as T
from ui import widgets as W


def _ping(url: str) -> float:
    started = time.perf_counter()
    requests.get(url.rstrip("/") + "/", timeout=2).raise_for_status()  # health check
    return (time.perf_counter() - started) * 1000


def _save_and_test(values: dict, to: str):
    saved = api.save_settings(values)
    api.send_test_email(to)
    return saved


class SystemSections:
    """Settings sections: backend & database, email (SMTP), audit log."""

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
