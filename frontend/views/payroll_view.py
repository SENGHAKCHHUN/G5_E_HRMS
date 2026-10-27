"""Screen 8 - Payroll & Payslips (Module 6). Filters, totals and paging come from the server."""
import csv
from tkinter import filedialog

import customtkinter as ctk

from core import tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from logic import labels
from logic.formatting import month_label, recent_months
from ui import theme as T
from ui import widgets as W
from views.payslip_dialog import STATUS_KIND, PayslipDialogs

STATUSES = ["Calculated", "Paid", "Pending"]
SEARCH_DELAY_MS = 350


def _load_overview(staff: bool, month: str, employee_id: int | None) -> dict:
    if staff:
        return {"summary": api.payroll_summary(month=month), "departments": api.get_departments()}
    return {"summary": api.payroll_summary(employee_id=employee_id),
            "latest": next(iter(api.payroll_page(employee_id=employee_id, limit=1).rows), None)}


class PayrollView(PayslipDialogs, ctk.CTkFrame):
    """Totals, filters, the payroll table, Calculate and Mark as Paid. Payslip and line edit:
    views/payslip_dialog.py."""

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
            header.add_action(_("Mark as Paid"), "primary", "check", self.mark_paid)
            header.add_action(_("Calculate Payroll"), "secondary", "bolt", self.calculate)

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
    def calculate(self):
        """Step 1: create and recalculate the unpaid lines. Nothing is paid yet, so lines can be reviewed."""
        period = month_label(self.month)
        message = _("Calculate payroll for {month} with today's salaries, rates and employment dates? "
                    "Unpaid lines are recalculated and keep their bonus and adjustment. Paid lines do not "
                    "change.").format(month=period)
        if not W.confirm(self, _("Calculate Payroll"), message, ok_text=_("Calculate"), kind="primary"):
            return

        def done(res):
            self.reload()
            W.toast(self, _("Payroll calculated: {created} new, {updated} updated, {removed} removed").format(
                created=res["created"], updated=res["calculated"], removed=res["removed"]))
        tasks.run(self, api.generate_payroll, self.month, on_done=done)

    def mark_paid(self):
        """Step 2: after review, mark the calculated lines as paid. Paid lines are locked."""
        period = month_label(self.month)
        calculated = self.summary.get("by_status", {}).get("Calculated", 0)
        if not calculated:
            W.toast(self, _("Nothing to pay for {month}. Calculate payroll first.").format(month=period), "info")
            return
        message = _("Mark {count} calculated line(s) for {month} as paid? Paid lines can no longer be "
                    "changed.").format(count=calculated, month=period)
        if not W.confirm(self, _("Mark as Paid"), message, ok_text=_("Mark as Paid"), kind="primary"):
            return

        def done(paid):
            self.reload()
            self.app.invalidate("dashboard")
            W.toast(self, _("Payroll batch complete: {count} payslips paid").format(count=paid))
        tasks.run(self, api.mark_paid, self.month, on_done=done)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"payroll_{self.month}.csv")
        if path:
            tasks.run(self, api.payroll_page, **self._filters(), on_done=lambda page: self._write_csv(path, page.rows))

    def _write_csv(self, path, rows):
        cols = ["code", "employee", "department", "month", "paid_days", "base_salary", "overtime_hours",
                "overtime_pay", "bonus", "adjustment", "unpaid_days", "unpaid_deduction", "tax", "pension",
                "insurance", "deductions", "net_salary", "status", "note"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        W.toast(self, _("Exported {count} payroll lines").format(count=len(rows)))
