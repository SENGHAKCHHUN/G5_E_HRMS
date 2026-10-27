"""Screen 7 - Leave Management (Module 5). The status filter and paging run on the server."""
from datetime import date, timedelta

import customtkinter as ctk

from core import tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from logic import leave as L
from logic.formatting import LEAVE_TYPES
from ui import theme as T
from ui import widgets as W
from views.common import submit

TYPE_COLOR = {"Annual": T.PRIMARY, "Sick": T.SUCCESS, "Casual": T.WARNING,
              "Maternity/Paternity": T.CATEGORY[4], "Unpaid": T.TEXT_3}
BALANCE_CARDS = [("Annual", "leave", "info", ("#93C5FD", "#A5B4FC")),
                 ("Sick", "medical", "success", T.SUCCESS),
                 ("Casual", "person", "info", T.PRIMARY)]
STATUSES = ["Pending", "Approved", "Rejected"]


def _load_overview(employee_id: int, staff: bool) -> dict:
    return {"balance": api.get_leave_balance(employee_id),
            "pending": api.leaves_page(employee_id=None if staff else employee_id, status="Pending", limit=1).total}


def _balance_title(key: str) -> str:
    return {"Annual": _("Annual Vacation"), "Sick": _("Sick & Medical"), "Casual": _("Personal / Casual")}[key]


class LeaveView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.staff = state.is_staff
        self.emp_id = state.session["employee_id"]
        self.all = _("All")
        self.status = "Pending" if self.staff else None

        header = W.PageHeader(self, _("Leave Management"),
                              _("Review, approve and track time-off across the organization") if self.staff
                              else _("Request time off and track your leave balances"), icon_name="leave")
        header.pack(fill="x")
        header.add_action(_("Apply Leave"), "primary", "add", self.apply_form)

        self.balances = W.transparent(self)
        self.balances.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(self.balances, 3)
        W.label(self.balances, _("Loading..."), color=T.TEXT_3).grid(row=0, column=0, pady=30)

        queue = W.card(self)
        queue.pack(fill="x", pady=(T.GAP, 0))
        head = W.transparent(queue)
        head.pack(fill="x", padx=18, pady=14)
        title_row = W.transparent(head)
        title_row.pack(side="left")
        ctk.CTkLabel(title_row, text="●", text_color=T.PRIMARY, font=T.font(14)).pack(side="left", padx=(0, 8))
        W.label(title_row, _("Leave Approval Queue") if self.staff else _("My Leave Requests"), size=16,
                weight="semibold").pack(side="left")
        self.pending_chip = W.tag(title_row, "", "info")
        self.pending_chip.pack(side="left", padx=10)
        seg = W.segmented(head, [L.translate_status(s) for s in STATUSES] + [self.all], command=self._filter_changed)
        seg.set(L.translate_status(self.status) if self.status else self.all)
        seg.pack(side="right")
        W.micro(head, _("Status Filter") + ":  ").pack(side="right")

        self.table = W.DataTable(queue, self._columns(), empty_text=_("No leave requests in this view"),
                                 row_height=60)
        self.table.configure(border_width=0, fg_color="transparent")
        self.table.pack(fill="x")
        self.pager = W.Paginator(self.table.footer, self.load_page, page_size=8)
        self.pager.pack(fill="x", pady=(6, 0))
        self.reload()

    def _columns(self):
        cols = [{"key": "id", "title": _("Request ID"), "weight": 9,
                 "render": lambda m, r: W.label(m, f"LV-{r['id']}", size=13, weight="semibold", color=T.PRIMARY)}]
        if self.staff:
            cols.append({"key": "employee", "title": _("Employee & Department"), "weight": 19,
                         "render": lambda m, r: W.person_cell(m, r["first_name"], r["last_name"], r["department"])})
        cols += [
            {"key": "type", "title": _("Leave Type"), "weight": 12,
             "render": lambda m, r: W.dot_text(m, L.translate_type(r["type"]), TYPE_COLOR.get(r["type"], T.TEXT_2))},
            {"key": "period", "title": _("Period"), "weight": 13,
             "render": lambda m, r: W.label(m, L.period_text(r["start_date"], r["end_date"]), size=12,
                                            wraplength=140, justify="left")},
            {"key": "days", "title": _("Duration"), "weight": 8,
             "render": lambda m, r: W.label(m, _("{count} day(s)").format(count=r["days"]), size=13,
                                            weight="semibold")},
            {"key": "status", "title": _("Status"), "weight": 10,
             "render": lambda m, r: W.badge(m, L.translate_status(r["status"]),
                                            L.STATUS_KIND.get(r["status"], "neutral"))},
            {"key": "actions", "title": _("Actions"), "weight": 21, "anchor": "e", "render": self._actions},
        ]
        return cols

    def _actions(self, master, r):
        box = W.transparent(master)
        if r["status"] == "Pending" and self.staff and r["employee_id"] != self.emp_id:
            W.button(box, _("Approve"), "success", "check", lambda: self.approve(r), height=30, size=12).pack(
                side="left", padx=2)
            W.button(box, _("Reject"), "danger", "close", lambda: self.reject(r), height=30, size=12).pack(
                side="left", padx=2)
        else:
            text = {"Rejected": _("View Reason"), "Approved": _("View Note")}.get(r["status"], _("View Request"))
            W.button(box, text, "ghost", "info", lambda: self.view(r), height=30, size=12).pack(side="left")
        return box

    # ------------------------------------------------------------------ data
    def reload(self):
        tasks.run(self, _load_overview, self.emp_id, self.staff, on_done=self._render_overview)
        self.load_page()

    def _render_overview(self, data: dict):
        self.pending_chip.configure(text=_("{count} pending").format(count=data["pending"]))
        self._build_balances(data["balance"])

    def _build_balances(self, bal: dict):
        for w in self.balances.winfo_children():
            w.destroy()
        for i, (key, ic, kind, color) in enumerate(BALANCE_CARDS):
            b = bal[key]
            share = b["remaining"] / b["allowance"] if b["allowance"] else 0
            c = W.card(self.balances)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))
            top = W.transparent(c)
            top.pack(fill="x", padx=18, pady=(16, 6))
            W.icon_tile(top, ic, kind, size=36, icon_size=17).pack(side="left")
            W.label(top, _balance_title(key), size=15, weight="semibold").pack(side="left", padx=10)
            W.tag(top, _("{percent}% left").format(percent=round(share * 100))).pack(side="right")
            row = W.transparent(c)
            row.pack(fill="x", padx=18)
            W.label(row, str(b["remaining"]), size=26, weight="bold").pack(side="left")
            W.label(row, "  " + _("/ {allowance} days remaining").format(allowance=b["allowance"]), size=12,
                    color=T.TEXT_2).pack(side="left", pady=(8, 0))
            W.label(row, _("{count} used").format(count=b["used"]), size=12, color=T.TEXT_2).pack(
                side="right", pady=(8, 0))
            W.progress(c, share, color).pack(fill="x", padx=18, pady=(8, 18))

    def load_page(self):
        self.table.set_loading()
        tasks.run(self, api.leaves_page, employee_id=None if self.staff else self.emp_id, status=self.status,
                  limit=self.pager.limit, offset=self.pager.offset, on_done=self._render_page)

    def _render_page(self, page):
        self.table.set_rows(page.rows)
        self.pager.update(page.total, len(page.rows))

    def _filter_changed(self, value):
        self.status = next((s for s in STATUSES if L.translate_status(s) == value), None)
        self.pager.reset()
        self.load_page()

    def on_show(self, apply=False, **_kw):
        if apply:
            self.after(100, self.apply_form)

    def _changed(self):
        self.reload()
        self.app.invalidate("dashboard", "employees", "attendance")

    # --------------------------------------------------------------- actions
    def approve(self, r):
        def done(_result):
            self._changed()
            W.toast(self, _("LV-{id} approved for {name}").format(id=r["id"], name=r["employee"]))
        tasks.run(self, api.approve_leave, r["id"], on_done=done)

    def reject(self, r):
        dlg = W.Modal(self, _("Reject LV-{id}").format(id=r["id"]),
                      f"{r['employee']} • {L.translate_type(r['type'])} • "
                      + _("{count} day(s)").format(count=r["days"]), width=480, height=380, scroll=False)
        f = W.Form(dlg.body, columns=1)
        box = f.textbox("note", _("Reason for rejection *"), height=110, span=1)
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)

        def done(_result):
            dlg.destroy()
            self._changed()
            W.toast(self, _("LV-{id} rejected").format(id=r["id"]), "danger")

        def do_reject():
            note = box.get("1.0", "end").strip()
            if not note:
                err.configure(text=_("Please provide a reason"))
                return
            submit(dlg, lambda: api.reject_leave(r["id"], note), err, done)

        dlg.add_button(_("Reject Request"), "danger", do_reject, "close")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)

    def view(self, r):
        lines = [_("Employee: {name} ({department})").format(name=r["employee"], department=r["department"]),
                 _("Type: {type}").format(type=L.translate_type(r["type"])),
                 _("Period: {period} ({count} day(s))").format(period=L.period_text(r["start_date"], r["end_date"]),
                                                               count=r["days"]),
                 _("Status: {status}").format(status=L.translate_status(r["status"])), "",
                 _("Reason: {reason}").format(reason=r["reason"] or "-")]
        if r.get("review_note"):
            lines.append(_("Reviewer note: {note}").format(note=r["review_note"]))
        W.info_dialog(self, _("Leave Request LV-{id}").format(id=r["id"]), "\n".join(lines), width=480, height=360)

    def apply_form(self):
        dlg = W.Modal(self, _("Submit Leave Request"), _("Your request will be sent to HR for approval"),
                      width=540, height=580)
        f = W.Form(dlg.body)
        f.option("type", _("Leave Type"), LEAVE_TYPES, span=2, labels={t: L.translate_type(t) for t in LEAVE_TYPES})
        start = date.today() + timedelta(days=1)
        f.entry("start_date", _("Start Date (YYYY-MM-DD)"), start.isoformat())
        f.entry("end_date", _("End Date (YYYY-MM-DD)"), start.isoformat())
        days_lbl = W.label(dlg.body, "", size=13, weight="semibold", color=T.PRIMARY)
        days_lbl.pack(anchor="w", padx=20, pady=(0, 4))
        f2 = W.Form(dlg.body, columns=1)
        f2.textbox("reason", _("Reason"), span=1, height=100)
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)
        balance: dict = {}
        tasks.run(dlg, api.get_leave_balance, self.emp_id, on_done=balance.update)

        def calc(*_args):
            v = f.values()
            days, problem = L.validate_request(v["start_date"], v["end_date"], v["type"], {},
                                               state.settings.get("work_week"))
            days_lbl.configure(text=problem or _("Calculated duration: {count} day(s)").format(count=days))
        for key in ("start_date", "end_date"):
            f.fields[key][1].bind("<KeyRelease>", calc)
        calc()

        def done(lv):
            dlg.destroy()
            self._changed()
            W.toast(self, _("Leave request LV-{id} submitted to HR").format(id=lv["id"]))

        def send():
            v = {**f.values(), **f2.values()}
            _days, problem = L.validate_request(v["start_date"], v["end_date"], v["type"], balance,
                                                state.settings.get("work_week"))
            if problem:
                err.configure(text=problem)
                return
            data = {"employee_id": self.emp_id, "type": v["type"], "start_date": v["start_date"],
                    "end_date": v["end_date"], "reason": v["reason"]}
            submit(dlg, lambda: api.submit_leave(data), err, done)

        dlg.add_button(_("Submit to HR"), "primary", send, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
