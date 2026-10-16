"""Screen 6 - Attendance & Time Tracking (Module 4). Filters and paging run on the server."""
import csv
from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from core import i18n, tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from logic import attendance as A
from logic import forms, labels
from logic.formatting import duration, month_label, recent_months
from ui import theme as T
from ui import widgets as W
from views.clock_card import ClockCard
from views.common import submit

STATUSES = ["On Time", "Late", "Absent", "Half Day", "On Leave"]
SEARCH_DELAY_MS = 350


def _load_overview(staff: bool, month: str, employee_id: int | None) -> dict:
    data = {"summary": api.attendance_summary(month=month, employee_id=employee_id)}
    if staff:
        data["stats"] = api.get_dashboard_stats()
        data["departments"] = api.get_departments()
    return data


def _find_and_add(values: dict) -> dict:
    """Look up the employee by code, then save the manual entry (runs in the background)."""
    code = values["code"].strip().lower()
    match = next((e for e in api.employees_page(search=code).rows if e["code"].lower() == code), None)
    data, problem = forms.manual_attendance(values, match["id"] if match else None)
    if problem:
        raise ValueError(problem)
    api.add_attendance(data)
    return match


class AttendanceView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.staff = state.is_staff
        self.months = recent_months(3)
        self.month = self.months[0]
        self.departments: list[dict] = []
        self.all_status, self.all_depts = _("All Statuses"), _("All Departments")
        self.status = None
        self._search_job = None
        self.ot_after = state.settings.get("overtime_after", "18:00")
        self.shift_start = state.settings.get("shift_start", "09:00")

        header = W.PageHeader(self, _("Attendance & Time Tracking"),
                              _("Shifts, punches and attendance for the whole team") if self.staff
                              else _("Your daily punches and monthly attendance history"), icon_name="clock")
        header.pack(fill="x")
        self.month_menu = W.option_menu(header.actions, [month_label(m) for m in self.months],
                                        command=self._month_changed, width=170, height=38)
        self.month_menu.pack(side="left")
        today = ctk.CTkFrame(header.actions, fg_color=T.ELEVATED, corner_radius=T.RADIUS_BTN, height=38)
        today.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(today, text="", image=W.icon("calendar", 14, T.SUCCESS)).pack(side="left", padx=(12, 6))
        W.label(today, _("Today:"), size=13, color=T.TEXT_2).pack(side="left")
        W.label(today, " " + i18n.format_date(date.today()), size=13, weight="semibold").pack(
            side="left", padx=(0, 12), pady=8)
        header.add_action(_("Export CSV"), "secondary", "download", self.export_csv)
        if self.staff:
            header.add_action(_("Manual Log Entry"), "primary", "add", self.manual_entry)

        # Check In / Check Out lives on this screen
        ClockCard(self, app, on_change=self.reload).pack(fill="x", pady=(T.GAP, 0))

        self.kpis = W.transparent(self)
        self.kpis.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(self.kpis, 4)

        bar = W.card(self)
        bar.pack(fill="x", pady=(T.GAP, 0))
        if self.staff:
            self.search = W.SearchEntry(bar, _("Filter by employee name or ID..."), width=280,
                                        on_change=lambda _t: self._search_later())
            self.search.pack(side="left", padx=(12, 8), pady=12)
            self.dept = W.option_menu(bar, [self.all_depts], command=lambda _v: self._filter_changed(), width=190)
            self.dept.pack(side="left", padx=(0, 8))
        self.seg = W.segmented(bar, [self.all_status] + [A.translate_status(s) for s in STATUSES],
                               command=self._status_changed)
        self.seg.set(self.all_status)
        self.seg.pack(side="right", padx=12, pady=12)

        self.table = W.DataTable(self, self._columns(), empty_text=_("No attendance records for this filter"))
        self.table.pack(fill="x", pady=(T.GAP, 0))
        self.pager = W.Paginator(self.table.footer, self.load_page, page_size=8)
        self.pager.pack(fill="x", pady=(6, 0))
        self.reload()

    def _columns(self):
        cols = [{"key": "date", "title": _("Date"), "weight": 8,
                 "render": lambda m, r: W.cell_stack(m, i18n.format_date(r["date"], "short"),
                                                     i18n.day_name(date.fromisoformat(r["date"]), short=True))}]
        if self.staff:
            cols += [
                {"key": "employee", "title": _("Employee"), "weight": 19,
                 "render": lambda m, r: W.person_cell(m, r["first_name"], r["last_name"], r["code"])},
                {"key": "department", "title": _("Department"), "weight": 12,
                 "render": lambda m, r: W.label(m, r["department"], size=12, wraplength=110, justify="left")},
            ]
        cols += [
            {"key": "shift", "title": _("Shift"), "weight": 9,
             "render": lambda m, r: W.tag(m, labels.show(labels.SHIFT, r["shift"]))},
            {"key": "check_in", "title": _("Check In"), "weight": 9,
             "render": lambda m, r: W.label(m, i18n.format_time(r["check_in"]), size=12, weight="semibold",
                                            color=T.DANGER if r["status"] == "Late" else T.TEXT)},
            {"key": "check_out", "title": _("Check Out"), "weight": 10, "render": self._checkout_cell},
            {"key": "hours", "title": _("Hours"), "weight": 8,
             "render": lambda m, r: W.label(m, duration(A.worked_seconds(r)), size=12, weight="semibold")},
            {"key": "ot", "title": _("OT"), "weight": 6, "render": self._ot_cell},
            {"key": "status", "title": _("Status"), "weight": 12,
             "render": lambda m, r: W.badge(m, A.status_label(r, self.shift_start),
                                            A.STATUS_KIND.get(r["status"], "neutral"))},
            {"key": "action", "title": _("Action"), "weight": 8, "anchor": "e",
             "render": lambda m, r: W.button(m, _("Details"), "secondary", command=lambda: self.details(r),
                                             height=28, size=11)},
        ]
        return cols

    @staticmethod
    def _checkout_cell(m, r):
        if A.in_progress(r):
            return W.label(m, _("In Progress"), size=11, color=T.TEXT_2)
        return W.label(m, i18n.format_time(r["check_out"]), size=12, weight="semibold")

    def _ot_cell(self, m, r):
        ot = A.overtime_seconds(r, self.ot_after)
        return W.label(m, _("+{minutes}m").format(minutes=int(ot // 60)) if ot else "--", size=12,
                       color=T.SUCCESS if ot else T.TEXT_3)

    # ------------------------------------------------------------------ data
    def _employee_id(self) -> int | None:
        return None if self.staff else state.session["employee_id"]

    def reload(self):
        tasks.run(self, _load_overview, self.staff, self.month, self._employee_id(), on_done=self._render_overview)
        self.load_page()

    def _render_overview(self, data: dict):
        if self.staff:
            self.departments = data["departments"]
            self.dept.configure(values=[self.all_depts] + [d["name"] for d in self.departments])
        self._build_kpis(data["summary"], data.get("stats"))

    def _build_kpis(self, s: dict, stats: dict | None):
        for w in self.kpis.winfo_children():
            w.destroy()
        avg = duration(s["avg_seconds"])
        shifts = _("{count} completed shifts").format(count=s["completed_shifts"])
        if stats:
            cards = [
                (_("Present Today"), f"{stats['present']} / {stats['expected']}", f"{stats['attendance_rate']:.1f}%",
                 "people", "success", _("{count} on time").format(count=stats["on_time"])),
                (_("Late Arrivals"), str(stats["late"]), _("today"), "stopwatch", "warning",
                 _("Grace period {minutes}m").format(minutes=state.settings.get("grace_minutes", 15))),
                (_("On Leave Today"), str(stats["on_leave_today"]), _("people"), "calendar", "neutral",
                 _("Approved absences")),
                (_("Avg Work Hours"), avg, month_label(self.month), "clock", "teal", shifts),
            ]
        else:
            cards = [
                (_("Days Worked"), str(s["worked_days"]), _("this month"), "calendar", "info",
                 month_label(self.month)),
                (_("On Time"), str(s["on_time"]), _("days"), "check", "success", _("Within grace period")),
                (_("Late Arrivals"), str(s["late"]), _("days"), "stopwatch", "warning",
                 _("Shift starts {time}").format(time=i18n.format_time(self.shift_start + ":00"))),
                (_("Avg Work Hours"), avg, _("per day"), "clock", "teal", shifts),
            ]
        for i, (title, value, unit, ic, kind, foot) in enumerate(cards):
            k = W.KpiCard(self.kpis, title, value, unit, ic, icon_kind=kind,
                          unit_color=T.SUCCESS if unit.endswith("%") else T.TEXT_2)
            W.label(k.footer, foot, size=12, color=T.TEXT_2).pack(side="left")
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 3 else 8))

    def _filters(self) -> dict:
        f = {"month": self.month, "employee_id": self._employee_id(), "status": self.status}
        if self.staff:
            f["search"] = self.search.get().strip() or None
            f["department_id"] = next((d["id"] for d in self.departments if d["name"] == self.dept.get()), None)
        return f

    def load_page(self):
        self.table.set_loading()
        tasks.run(self, api.attendance_page, **self._filters(), limit=self.pager.limit, offset=self.pager.offset,
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
        self.status = next((s for s in STATUSES if A.translate_status(s) == value), None)
        self._filter_changed()

    def _month_changed(self, label):
        self.month = next(m for m in self.months if month_label(m) == label)
        self.pager.reset()
        self.reload()

    # --------------------------------------------------------------- actions
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"attendance_{self.month}.csv")
        if path:
            tasks.run(self, api.attendance_page, **self._filters(),
                      on_done=lambda page: self._write_csv(path, page.rows))

    def _write_csv(self, path, rows):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["date", "code", "employee", "department", "check_in", "check_out", "hours", "status"])
            for r in rows:
                w.writerow([r["date"], r["code"], r["employee"], r["department"], r["check_in"] or "",
                            r["check_out"] or "", round(A.worked_seconds(r) / 3600, 2), r["status"]])
        W.toast(self, _("Exported {count} attendance records").format(count=len(rows)))

    def details(self, r):
        dlg = W.Modal(self, _("Attendance Record"), f"{r['employee']} • {r['code']}", width=460, height=470,
                      scroll=False)
        box = W.card(dlg.body, fg=T.SURFACE_ALT)
        box.pack(fill="x", padx=12, pady=8)
        box.grid_columnconfigure((0, 1), weight=1, uniform="d")
        fields = [(_("Date"), i18n.format_date(r["date"])), (_("Department"), r["department"]),
                  (_("Shift"), labels.show(labels.SHIFT, r["shift"])),
                  (_("Status"), A.status_label(r, self.shift_start)),
                  (_("Check In"), i18n.format_time(r["check_in"])), (_("Check Out"), i18n.format_time(r["check_out"])),
                  (_("Total Hours"), duration(A.worked_seconds(r))),
                  (_("Overtime"), duration(A.overtime_seconds(r, self.ot_after)))]
        for i, (k, v) in enumerate(fields):
            cell = W.transparent(box)
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=16, pady=8)
            W.micro(cell, k).pack(anchor="w")
            W.label(cell, v, size=14, weight="semibold").pack(anchor="w")
        dlg.add_button(_("Close"), "primary", dlg.destroy)

    def manual_entry(self):
        dlg = W.Modal(self, _("Manual Log Entry"), _("Record a missed punch on behalf of an employee"), height=520)
        f = W.Form(dlg.body)
        f.entry("code", _("Employee ID *"), "", _("e.g. EMP-012"), span=2)
        f.entry("date", _("Date * (YYYY-MM-DD)"), date.today().isoformat())
        f.option("status", _("Status"), STATUSES[:4],
                 labels={s: A.translate_status(s) for s in STATUSES[:4]})
        f.entry("check_in", _("Check In (HH:MM)"), "09:00")
        f.entry("check_out", _("Check Out (HH:MM)"), "18:00")
        f.textbox("note", _("Reason / Note"), height=70)
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)

        def done(emp):
            dlg.destroy()
            self.reload()
            self.app.invalidate("dashboard")
            W.toast(self, _("Log entry saved for {name}").format(name=emp["full_name"]))

        def save():
            values = f.values()
            if not values["code"].strip():
                err.configure(text=_("Unknown employee ID."))
                return
            submit(dlg, lambda: _find_and_add(values), err, done)

        dlg.add_button(_("Save Entry"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
