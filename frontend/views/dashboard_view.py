"""Screen 3 - Dashboard (Module 7). Staff see company figures, employees a personal overview."""
from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from core import i18n, tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from logic import attendance as A
from logic import labels
from logic import leave as L
from ui import theme as T
from ui import widgets as W
from ui.icons import icon

ATTENDANCE_TARGET = 90  # % shown as "on track" on the attendance card


def _load_company() -> dict:
    return {"stats": api.get_dashboard_stats(), "checkins": api.recent_checkins(5)}


def _load_personal(employee_id: int) -> dict:
    month = date.today().strftime("%Y-%m")
    return {"today": api.today_record(), "summary": api.attendance_summary(month=month),
            "recent": api.attendance_page(month=month, limit=6).rows, "balance": api.get_leave_balance(employee_id),
            "payslip": next(iter(api.payroll_page(limit=1).rows), None), "leaves": api.leaves_page(limit=6).rows}


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        if state.is_staff:
            self._header_company()
        else:
            self._header_personal()
        self.body = W.transparent(self)
        self.body.pack(fill="both", expand=True)
        W.label(self.body, _("Loading..."), color=T.TEXT_3, anchor="center").pack(fill="x", pady=60)
        if state.is_staff:
            tasks.run(self, _load_company, on_done=self._render_company)
        else:
            tasks.run(self, _load_personal, state.session["employee_id"], on_done=self._render_personal)

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    # ============================================================ company
    def _header_company(self):
        header = W.PageHeader(self, _("Dashboard Overview"), _("Today's staffing, attendance and approvals"),
                              eyebrow=_("Overview"))
        header.pack(fill="x")
        header.add_action(_("Export PDF Summary"), "secondary", "document", self._export)
        header.add_action(_("Refresh Data"), "primary", "refresh", lambda: self.app.refresh_view())

    def _render_company(self, data: dict):
        self._clear_body()
        s = data["stats"]
        kpis = W.transparent(self.body)
        kpis.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(kpis, 4)

        k = W.KpiCard(kpis, _("Total Employees"), str(s["total_employees"]), _("employees"), "people")
        W.badge(k.footer, _("+{count} hired").format(count=s["new_this_month"]), "success", dot=False).pack(side="left")
        W.label(k.footer, "  " + _("this month"), size=12, color=T.TEXT_2).pack(side="left")
        k.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        k = W.KpiCard(kpis, _("On Leave Today"), str(s["on_leave_today"]), _("staff"), "calendar")
        types = sorted(s["leave_types"].items(), key=lambda item: -item[1])
        for name, n in types[:2]:
            W.tag(k.footer, f"{n} {L.translate_type(name)}").pack(side="left", padx=(0, 6))
        if len(types) > 2:
            W.tag(k.footer, f"+{sum(n for _name, n in types[2:])}").pack(side="left")
        k.grid(row=0, column=1, sticky="nsew", padx=8)

        rate = s["attendance_rate"]
        on_track = rate >= ATTENDANCE_TARGET
        k = W.KpiCard(kpis, _("Attendance Rate"), f"{rate:.1f}%",
                      _("on track") if on_track else _("below {target}%").format(target=ATTENDANCE_TARGET), "clock",
                      unit_color=T.SUCCESS if on_track else T.WARNING)
        W.tag(k.footer, f"{s['present']} / {s['expected']}", "info").pack(side="left")
        W.label(k.footer, "  " + _("clocked in today"), size=12, color=T.TEXT_2).pack(side="left")
        k.grid(row=0, column=2, sticky="nsew", padx=8)

        k = W.KpiCard(kpis, _("Pending Approvals"), str(s["pending_leaves"]), _("requests"), "warning",
                      icon_kind="danger", value_color=T.DANGER if s["pending_leaves"] else T.TEXT)
        W.label(k.footer, _("Leave requests awaiting review"), size=12, color=T.TEXT_2).pack(side="left")
        k.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        mid = W.transparent(self.body)
        mid.pack(fill="x", pady=(T.GAP, 0))
        mid.grid_columnconfigure(0, weight=3, uniform="mid")
        mid.grid_columnconfigure(1, weight=2, uniform="mid")
        self._headcount_card(mid, s).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._checkin_card(mid, data["checkins"]).grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        qa_head = W.transparent(self.body)
        qa_head.pack(fill="x", pady=(T.GAP + 4, 8))
        W.micro(qa_head, _("Quick Actions")).pack(side="left")
        qa = W.transparent(self.body)
        qa.pack(fill="x")
        W.grid_columns(qa, 3)
        month = i18n.month_label(date.today().strftime("%Y-%m"))
        actions = [
            (_("Run Payroll"), _("{month} • {count} employees").format(month=month, count=s["total_employees"]),
             "payroll", "info", lambda: self.app.navigate("payroll")),
            (_("Review Leave Requests"), _("{count} waiting for a decision").format(count=s["pending_leaves"]),
             "check", "neutral", lambda: self.app.navigate("leave")),
            (_("Add Employee"), _("Create the profile and login"), "add_person", "success",
             lambda: self.app.navigate("employees", add=True)),
        ]
        for i, (title, sub, ic, kind, cmd) in enumerate(actions):
            self._quick_action(qa, title, sub, ic, kind, cmd).grid(
                row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))

    def _headcount_card(self, master, s):
        c = W.card(master)
        top = W.transparent(c)
        top.pack(fill="x", padx=20, pady=(18, 10))
        W.section_title(top, _("Headcount by Department"), _("Employees and monthly base salaries")).pack(side="left")
        quarter = (date.today().month - 1) // 3 + 1
        W.tag(top, f"Q{quarter} {date.today().year}").pack(side="right", anchor="n")

        depts = sorted(s["departments"], key=lambda d: d["headcount"], reverse=True)
        total = sum(d["headcount"] for d in depts) or 1
        largest = max((d["headcount"] for d in depts), default=1) or 1
        for d in depts:
            color = T.CATEGORY[(d["id"] - 1) % len(T.CATEGORY)]
            row = W.transparent(c)
            row.pack(fill="x", padx=20, pady=(8, 0))
            ctk.CTkLabel(row, text="●", text_color=color, font=T.font(11), width=12).pack(side="left")
            W.label(row, d["name"], size=14, weight="semibold").pack(side="left", padx=(6, 6))
            W.label(row, _("({count} people)").format(count=d["headcount"]), size=12, color=T.TEXT_2).pack(side="left")
            W.label(row, f"{d['headcount'] / total * 100:.0f}%", size=14, weight="bold", color=color).pack(side="right")
            W.label(row, _("{amount}/mo").format(amount=W.money(d["payroll"])) + "   ", size=12,
                    color=T.TEXT_2).pack(side="right")
            W.progress(c, d["headcount"] / largest * 0.9, color=color).pack(fill="x", padx=20, pady=(6, 2))

        foot = ctk.CTkFrame(c, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        foot.pack(fill="x", padx=20, pady=(18, 20))
        ctk.CTkLabel(foot, text="", image=icon("check", 15, T.SUCCESS)).pack(side="left", padx=(14, 8), pady=12)
        W.label(foot, _("Monthly base payroll: {amount}").format(amount=W.money(s["monthly_payroll"])), size=13,
                weight="semibold").pack(side="left")
        W.button(foot, _("View departments") + " →", "link", height=30, size=12,
                 command=lambda: self.app.navigate("departments")).pack(side="right", padx=8)
        return c

    def _checkin_card(self, master, rows):
        c = W.card(master)
        top = W.transparent(c)
        top.pack(fill="x", padx=20, pady=(18, 10))
        W.section_title(top, _("Today's Check-Ins"), _("The latest employees to clock in"), dot=T.SUCCESS).pack(
            side="left")
        well = ctk.CTkFrame(c, fg_color=T.INPUT, corner_radius=T.RADIUS_CARD)
        well.pack(fill="both", expand=True, padx=20)
        if not rows:
            W.label(well, _("No check-ins recorded yet today."), color=T.TEXT_2,
                    anchor="center").pack(fill="x", pady=30)
        shift_start = state.settings.get("shift_start", "09:00")
        for r in rows:
            item = ctk.CTkFrame(well, fg_color=T.SURFACE, corner_radius=T.RADIUS_BTN)
            item.pack(fill="x", padx=6, pady=4)
            W.avatar(item, r["first_name"], r["last_name"], size=38).pack(side="left", padx=10, pady=8)
            W.cell_stack(item, r["employee"], r["department"]).pack(side="left")
            right = W.transparent(item)
            right.pack(side="right", padx=12)
            late = r["status"] == "Late"
            W.label(right, i18n.format_time(r["check_in"]), size=13, weight="semibold",
                    color=T.DANGER if late else T.TEXT, anchor="e").pack(anchor="e")
            color = {"Late": T.DANGER, "Half Day": T.WARNING}.get(r["status"], T.SUCCESS)
            W.label(right, "● " + A.status_label(r, shift_start), size=11, weight="semibold", color=color,
                    anchor="e").pack(anchor="e")
        W.button(c, _("View All Attendance") + "  →", "soft", height=38,
                 command=lambda: self.app.navigate("attendance")).pack(fill="x", padx=20, pady=(12, 20))
        return c

    def _quick_action(self, master, title, sub, icon_name, kind, command):
        c = W.card(master)
        W.icon_tile(c, icon_name, kind, size=46, icon_size=20).pack(side="left", padx=(18, 14), pady=16)
        W.cell_stack(c, title, sub).pack(side="left")
        ctk.CTkLabel(c, text="", image=icon("chevron_right", 14, T.TEXT_2)).pack(side="right", padx=16)
        W.make_clickable(c, command, hover_frame=c, hover=T.ROW_HOVER, base=T.SURFACE)
        return c

    def _export(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            initialfile=f"dashboard_summary_{date.today():%Y%m%d}.pdf")
        if path:
            tasks.run(self, api.summary_pdf, on_done=lambda data: self._saved(path, data))

    def _saved(self, path: str, data: bytes):
        with open(path, "wb") as f:
            f.write(data)
        W.toast(self, _("Dashboard summary saved as PDF"))

    # =========================================================== personal
    def _header_personal(self):
        sess = state.session
        header = W.PageHeader(self, _("Welcome back, {name}").format(name=sess["name"].split()[0]),
                              f"{sess['position']} • {sess['department']}", eyebrow=_("My Overview"))
        header.pack(fill="x")
        header.add_action(_("Request Leave"), "secondary", "calendar", lambda: self.app.navigate("leave", apply=True))
        header.add_action(_("Clock In / Out"), "primary", "clock", lambda: self.app.navigate("attendance"))

    def _render_personal(self, data: dict):
        self._clear_body()
        today, summary, balance, last = data["today"], data["summary"], data["balance"], data["payslip"]
        kpis = W.transparent(self.body)
        kpis.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(kpis, 4)

        punched = bool(today and today.get("check_in"))
        k = W.KpiCard(kpis, _("Today"), i18n.format_time(today["check_in"]) if punched else "--:--",
                      _("clocked in") if punched else _("not clocked in"), "clock")
        W.badge(k.footer, A.translate_status(today["status"]) if punched else _("Awaiting check-in"),
                "success" if punched and today["status"] == "On Time" else "warning").pack(side="left")
        k.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        k = W.KpiCard(kpis, _("Punctuality (Month)"), f"{A.punctuality(summary):.0f}%", _("on time"), "trend")
        W.tag(k.footer, _("{count} days worked").format(count=summary["worked_days"]), "info").pack(side="left")
        k.grid(row=0, column=1, sticky="nsew", padx=8)

        annual = balance["Annual"]
        k = W.KpiCard(kpis, _("Annual Leave"), str(annual["remaining"]),
                      _("/ {days} days left").format(days=annual["allowance"]), "leave", icon_kind="success")
        W.progress(k.footer, annual["remaining"] / annual["allowance"], T.SUCCESS).pack(fill="x", pady=6)
        k.grid(row=0, column=2, sticky="nsew", padx=8)

        k = W.KpiCard(kpis, _("Latest Net Pay"), W.money(last["net_salary"]) if last else "-", "", "payroll",
                      icon_kind="teal", value_color=T.TEAL)
        if last:
            W.badge(k.footer, labels.show(labels.PAYROLL_STATUS, last["status"]),
                    "success" if last["status"] == "Paid" else "info").pack(side="left")
        k.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        row = W.transparent(self.body)
        row.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(row, 2, uniform="p")

        c = W.card(row)
        c.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        W.section_title(c, _("My Recent Attendance"), _("This month")).pack(fill="x", padx=20, pady=(18, 10))
        for r in data["recent"]:
            item = ctk.CTkFrame(c, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
            item.pack(fill="x", padx=20, pady=3)
            W.label(item, i18n.format_date(r["date"], "short"), size=13, weight="semibold").pack(
                side="left", padx=12, pady=10)
            W.label(item, f"{i18n.format_time(r['check_in'])}  →  {i18n.format_time(r['check_out'])}", size=12,
                    color=T.TEXT_2).pack(side="left", padx=12)
            W.badge(item, A.translate_status(r["status"]), A.STATUS_KIND.get(r["status"], "neutral")).pack(
                side="right", padx=12)
        W.button(c, _("Open Attendance") + "  →", "soft", height=36,
                 command=lambda: self.app.navigate("attendance")).pack(fill="x", padx=20, pady=(10, 20))

        c = W.card(row)
        c.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        W.section_title(c, _("My Leave Requests"), _("Your latest requests")).pack(fill="x", padx=20, pady=(18, 10))
        if not data["leaves"]:
            W.label(c, _("No leave requests yet."), color=T.TEXT_2).pack(padx=20, pady=20)
        for lv in data["leaves"]:
            item = ctk.CTkFrame(c, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
            item.pack(fill="x", padx=20, pady=3)
            W.cell_stack(item, _("{type} leave • {days} day(s)").format(type=L.translate_type(lv["type"]),
                                                                          days=lv["days"]),
                         L.period_text(lv["start_date"], lv["end_date"])).pack(side="left", padx=12, pady=6)
            W.badge(item, L.translate_status(lv["status"]), L.STATUS_KIND.get(lv["status"], "neutral")).pack(
                side="right", padx=12)
        W.button(c, _("Open Leave Management") + "  →", "soft", height=36,
                 command=lambda: self.app.navigate("leave")).pack(fill="x", padx=20, pady=(10, 20))
