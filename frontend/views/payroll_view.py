"""Screen 8 - Payroll & Payslips (Module 6). Filters, totals and paging come from the server."""
import csv
from tkinter import filedialog

import customtkinter as ctk

from core import tasks
from core.api_client import ApiError, api
from core.i18n import _
from core.state import state
from logic import labels
from logic.formatting import month_label, recent_months
from ui import theme as T
from ui import widgets as W
from ui.icons import logo

STATUS_KIND = {"Calculated": "info", "Paid": "success", "Pending": "neutral"}
STATUSES = ["Calculated", "Paid", "Pending"]
SEARCH_DELAY_MS = 350


def _load_overview(staff: bool, month: str, employee_id: int | None) -> dict:
    if staff:
        return {"summary": api.payroll_summary(month=month), "departments": api.get_departments()}
    return {"summary": api.payroll_summary(employee_id=employee_id),
            "latest": next(iter(api.payroll_page(employee_id=employee_id, limit=1).rows), None)}


def _run_batch(month: str) -> int:
    api.generate_payroll(month)
    return api.mark_paid(month)


class PayrollView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.staff = state.is_staff
        self.months = recent_months(3)
        self.month = self.months[0]
        self.status = None
        self.summary: dict = {}
        self.departments: list[dict] = []
        self.all_depts = _("All Departments")
        self._search_job = None

        header = W.PageHeader(self, _("Payroll & Salary Processing") if self.staff else _("My Payslips"),
                              _("Calculate net salary from base pay, allowances and deductions") if self.staff
                              else _("Monthly salary statements and deductions"), icon_name="payroll")
        header.pack(fill="x")
        if self.staff:
            self.month_menu = W.option_menu(header.actions, [month_label(m) for m in self.months],
                                            command=self._month_changed, width=170, height=38)
            self.month_menu.pack(side="left")
            header.add_action(_("Export CSV"), "secondary", "download", self.export_csv)
            header.add_action(_("Run Payroll Batch"), "primary", "bolt", self.run_batch)

        self.kpis = W.transparent(self)
        self.kpis.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(self.kpis, 3)
        W.label(self.kpis, _("Loading..."), color=T.TEXT_3).grid(row=0, column=0, pady=30)

        if self.staff:
            bar = W.card(self)
            bar.pack(fill="x", pady=(T.GAP, 0))
            self.search = W.SearchEntry(bar, _("Filter by ID or employee..."), width=320,
                                        on_change=lambda _t: self._search_later())
            self.search.pack(side="left", padx=(12, 8), pady=12)
            self.dept = W.option_menu(bar, [self.all_depts], command=lambda _v: self._filter_changed(), width=200)
            self.dept.pack(side="left")
            self.seg = W.segmented(bar, [_("All")], command=self._status_changed)
            self.seg.pack(side="right", padx=12)

        self.table = W.DataTable(self, self._columns(), empty_text=_("No payroll records"))
        self.table.pack(fill="x", pady=(T.GAP, 0))
        self.pager = W.Paginator(self.table.footer, self.load_page, page_size=8)
        self.pager.pack(fill="x", pady=(6, 0))
        self.reload()

    def _columns(self):
        def amount(key, color=T.TEXT, sign=False, weight="normal"):
            return lambda m, r: W.label(m, W.money(r[key] if key != "deductions" else -r[key], sign=sign), size=13,
                                        color=color, weight=weight, anchor="e")
        if self.staff:
            cols = [
                {"key": "code", "title": _("Emp ID"), "weight": 8,
                 "render": lambda m, r: W.tag(m, r["code"], mono=True)},
                {"key": "employee", "title": _("Employee Name"), "weight": 19,
                 "render": lambda m, r: W.person_cell(m, r["first_name"], r["last_name"], r["email"])},
                {"key": "department", "title": _("Department"), "weight": 12,
                 "render": lambda m, r: W.label(m, r["department"], size=12, wraplength=105, justify="left")},
            ]
        else:
            cols = [{"key": "month", "title": _("Pay Period"), "weight": 14,
                     "render": lambda m, r: W.label(m, month_label(r["month"]), size=13, weight="semibold")}]
        cols += [
            {"key": "base_salary", "title": _("Base"), "weight": 10, "anchor": "e", "render": amount("base_salary")},
            {"key": "bonus", "title": _("Bonus"), "weight": 9, "anchor": "e",
             "render": amount("bonus", T.SUCCESS, sign=True)},
            {"key": "deductions", "title": _("Deductions"), "weight": 10, "anchor": "e",
             "render": amount("deductions", T.DANGER, sign=True)},
            {"key": "net_salary", "title": _("Net Salary"), "weight": 11, "anchor": "e",
             "render": amount("net_salary", weight="bold")},
            {"key": "status", "title": _("Status"), "weight": 12, "anchor": "center",
             "render": lambda m, r: W.badge(m, labels.show(labels.PAYROLL_STATUS, r["status"]),
                                            STATUS_KIND.get(r["status"], "neutral"))},
            {"key": "action", "title": _("Action"), "weight": 11, "anchor": "e",
             "render": lambda m, r: W.button(m, _("Payslip"), "secondary", "print",
                                             lambda: self.payslip(r), height=30, size=12)},
        ]
        return cols

    # ------------------------------------------------------------------ data
    def _employee_id(self) -> int | None:
        return None if self.staff else state.session["employee_id"]

    def reload(self):
        tasks.run(self, _load_overview, self.staff, self.month, self._employee_id(), on_done=self._render_overview)
        self.load_page()

    def _render_overview(self, data: dict):
        self.summary = data["summary"]
        if self.staff:
            self.departments = data["departments"]
            self.dept.configure(values=[self.all_depts] + [d["name"] for d in self.departments])
            self._render_status_counts()
        self._build_kpis(data.get("latest"))

    def _status_label(self, status: str | None) -> str:
        counts = self.summary.get("by_status", {})
        if status is None:
            return _("All ({count})").format(count=self.summary.get("count", 0))
        return f"{labels.show(labels.PAYROLL_STATUS, status)} ({counts.get(status, 0)})"

    def _render_status_counts(self):
        self.seg.configure(values=[self._status_label(s) for s in [None, *STATUSES]])
        self.seg.set(self._status_label(self.status))

    def _build_kpis(self, latest: dict | None):
        for w in self.kpis.winfo_children():
            w.destroy()
        s = self.summary
        settings = state.settings
        if self.staff:
            done = s["count"] - s["by_status"].get("Pending", 0)
            cards = [
                (_("Total Payroll Outflow"), W.money(s["gross"]), "bank", "info", T.TEXT,
                 _("{count} employees").format(count=s["count"]),
                 _("{percent}% calculated").format(percent=round(done / s["count"] * 100) if s["count"] else 0)),
                (_("Tax Withholding"), W.money(s["tax"]), "document", "neutral", T.TEXT, _("Income tax"),
                 _("{rate}% rate").format(rate=round(settings.get("tax_rate", 0)))),
                (_("Net Disbursement"), W.money(s["net"]), "payroll", "success", T.SUCCESS, month_label(self.month),
                 _("Pay day {day}").format(day=settings.get("pay_day", "-"))),
            ]
        else:
            cards = [
                (_("Latest Net Pay"), W.money(latest["net_salary"]) if latest else "-", "payroll", "success",
                 T.SUCCESS, month_label(latest["month"]) if latest else "",
                 labels.show(labels.PAYROLL_STATUS, latest["status"]) if latest else ""),
                (_("Total Net Received"), W.money(s["net"]), "bank", "info", T.TEXT,
                 _("{count} payslips").format(count=s["count"]), ""),
                (_("Total Tax Withheld"), W.money(s["tax"]), "document", "neutral", T.TEXT, _("Income tax"), ""),
            ]
        for i, (title, value, ic, kind, color, foot_l, foot_r) in enumerate(cards):
            k = W.KpiCard(self.kpis, title, value, "", ic, icon_kind=kind, value_color=color)
            W.label(k.footer, foot_l, size=12, weight="semibold", color=T.SUCCESS if i == 0 else T.TEXT_2).pack(
                side="left")
            W.label(k.footer, foot_r, size=12, color=T.TEXT_2).pack(side="right")
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))

    def _filters(self) -> dict:
        if not self.staff:
            return {"employee_id": self._employee_id()}
        return {"month": self.month, "status": self.status, "search": self.search.get().strip() or None,
                "department_id": next((d["id"] for d in self.departments if d["name"] == self.dept.get()), None)}

    def load_page(self):
        self.table.set_loading()
        tasks.run(self, api.payroll_page, **self._filters(), limit=self.pager.limit, offset=self.pager.offset,
                  on_done=self._render_page)

    def _render_page(self, page):
        self.table.set_rows(page.rows)
        self.pager.update(page.total, len(page.rows))

    def _search_later(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(SEARCH_DELAY_MS, self._filter_changed)

    def _filter_changed(self):
        self._search_job = None
        self.pager.reset()
        self.load_page()

    def _status_changed(self, value):
        self.status = next((s for s in STATUSES if self._status_label(s) == value), None)
        self._filter_changed()

    def _month_changed(self, label):
        self.month = next(m for m in self.months if month_label(m) == label)
        self.status = None
        self.pager.reset()
        self.reload()

    # --------------------------------------------------------------- actions
    def run_batch(self):
        counts = self.summary.get("by_status", {})
        pending, calculated = counts.get("Pending", 0), counts.get("Calculated", 0)
        period = month_label(self.month)
        if self.summary.get("count") and not pending and not calculated:
            W.toast(self, _("Payroll for {month} is already fully paid").format(month=period), "info")
            return
        message = _("{month}\n\n• Calculate {pending} pending line(s)\n• Mark {total} line(s) as paid\n\n"
                    "Continue?").format(month=period, pending=pending, total=pending + calculated)
        if not W.confirm(self, _("Run Payroll Batch"), message, ok_text=_("Run Batch"), kind="primary"):
            return

        def done(paid):
            self.reload()
            self.app.invalidate("dashboard")
            W.toast(self, _("Payroll batch complete: {count} payslips paid").format(count=paid))
        tasks.run(self, _run_batch, self.month, on_done=done)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"payroll_{self.month}.csv")
        if path:
            tasks.run(self, api.payroll_page, **self._filters(), on_done=lambda page: self._write_csv(path, page.rows))

    def _write_csv(self, path, rows):
        cols = ["code", "employee", "department", "month", "base_salary", "bonus", "tax", "pension",
                "insurance", "deductions", "net_salary", "status"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        W.toast(self, _("Exported {count} payroll lines").format(count=len(rows)))

    def payslip(self, r):
        dlg = W.Modal(self, _("Monthly Payslip"), f"{r['employee']} • {month_label(r['month'])}",
                      width=520, height=700)
        b = dlg.body
        s = state.settings
        head = W.card(b, fg=T.SURFACE_ALT)
        head.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkLabel(head, text="", image=logo(40)).pack(side="left", padx=14, pady=14)
        box = W.transparent(head)
        box.pack(side="left")
        W.label(box, s.get("company_name", ""), size=15, weight="bold").pack(anchor="w")
        W.label(box, s.get("domain", ""), size=11, color=T.TEXT_2).pack(anchor="w")
        W.badge(head, labels.show(labels.PAYROLL_STATUS, r["status"]), STATUS_KIND.get(r["status"], "neutral")).pack(
            side="right", padx=14)

        info = W.transparent(b)
        info.pack(fill="x", padx=12, pady=4)
        info.grid_columnconfigure((0, 1), weight=1, uniform="i")
        for i, (k, v) in enumerate([(_("Employee"), r["employee"]), (_("Employee ID"), r["code"]),
                                    (_("Department"), r["department"]), (_("Pay Period"), month_label(r["month"]))]):
            cell = W.transparent(info)
            cell.grid(row=i // 2, column=i % 2, sticky="w", pady=4)
            W.micro(cell, k).pack(anchor="w")
            W.label(cell, v, size=13, weight="semibold").pack(anchor="w")

        def section(title, items, total_label, total, color):
            c = W.card(b)
            c.pack(fill="x", padx=8, pady=6)
            W.micro(c, title).pack(anchor="w", padx=14, pady=(12, 4))
            for name, val in items:
                row = W.transparent(c)
                row.pack(fill="x", padx=14, pady=2)
                W.label(row, name, size=13, color=T.TEXT_2).pack(side="left")
                W.label(row, W.money(val), size=13, mono=True).pack(side="right")
            W.divider(c).pack(fill="x", padx=14, pady=6)
            row = W.transparent(c)
            row.pack(fill="x", padx=14, pady=(0, 12))
            W.label(row, total_label, size=13, weight="semibold").pack(side="left")
            W.label(row, W.money(total), size=13, weight="bold", color=color).pack(side="right")

        section(_("Earnings"), [(_("Base Salary"), r["base_salary"]), (_("Allowances / Bonus"), r["bonus"])],
                _("Gross Earnings"), r["base_salary"] + r["bonus"], T.SUCCESS)
        section(_("Deductions"), [(_("Income Tax ({rate}%)").format(rate=round(s.get("tax_rate", 0))), r["tax"]),
                                  (_("Pension ({rate}%)").format(rate=round(s.get("pension_rate", 0))), r["pension"]),
                                  (_("Health Insurance"), r["insurance"])],
                _("Total Deductions"), r["deductions"], T.DANGER)

        net = ctk.CTkFrame(b, fg_color=T.BADGE["teal"][0], corner_radius=T.RADIUS_CARD)
        net.pack(fill="x", padx=8, pady=(6, 8))
        W.label(net, _("NET PAY"), size=12, weight="semibold", color=T.BADGE["teal"][1]).pack(
            side="left", padx=16, pady=18)
        W.label(net, W.money(r["net_salary"]), size=26, weight="bold", color=T.BADGE["teal"][1]).pack(
            side="right", padx=16)

        def failed(error):
            if not isinstance(error, ApiError):
                raise error
            W.toast(dlg, str(error), "danger", ms=6000)

        def write_pdf(path, data):
            with open(path, "wb") as fh:
                fh.write(data)
            W.toast(dlg, _("Payslip saved as PDF"))

        def save():
            path = filedialog.asksaveasfilename(parent=dlg, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                                initialfile=f"payslip_{r['code']}_{r['month']}.pdf")
            if path:
                tasks.run(dlg, api.payslip_pdf, r["id"], on_done=lambda data: write_pdf(path, data), on_error=failed)

        def email():
            tasks.run(dlg, api.email_payslip, r["id"], on_error=failed,
                      on_done=lambda res: W.toast(dlg, _("Payslip emailed to {to}").format(to=res["to"])))

        dlg.add_button(_("Save PDF"), "primary", save, "download")
        if self.staff:
            dlg.add_button(_("Email to Employee"), "secondary", email, "mail")
