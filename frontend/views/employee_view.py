"""Screen 4 - Employee Directory (Module 2). Search, filters and paging run on the server."""
import csv
from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from core import i18n, tasks
from core.api_client import ApiError, api
from core.i18n import _
from logic import forms, labels
from ui import theme as T
from ui import widgets as W

STATUS_KIND = {"Active": "success", "On Leave": "neutral", "Probation": "info", "Terminated": "danger"}
SEARCH_DELAY_MS = 350


def _load_overview() -> dict:
    return {"departments": api.get_departments(), "summary": api.employee_summary(),
            "stats": api.get_dashboard_stats()}


class EmployeeView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.departments: list[dict] = []
        self.all_depts, self.all_roles, self.all_status = _("All Departments"), _("All Roles"), _("All Statuses")
        self.status_names = labels.choices({k: v for k, v in labels.EMPLOYEE_STATUS.items() if k != "Terminated"})
        self._search_job = None

        self.header = W.PageHeader(self, _("Employee Directory"),
                                   _("Manage employee profiles, departments and system roles."), chip="",
                                   icon_name="people")
        self.header.pack(fill="x")
        self.header.add_action(_("Export CSV"), "secondary", "download", self.export_csv)
        self.header.add_action(_("Add Employee"), "primary", "add", lambda: self.open_form())

        top = W.transparent(self)
        top.pack(fill="x", pady=(T.GAP, 0))
        top.grid_columnconfigure(0, weight=10, uniform="top")
        top.grid_columnconfigure(1, weight=24, uniform="top")
        self.spread = W.card(top)
        self.spread.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        W.label(self.spread, _("Loading..."), color=T.TEXT_3).pack(padx=16, pady=40)
        self._build_filters(top).grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.table = W.DataTable(self, self._columns(), empty_text=_("No employees match your filters"))
        self.table.pack(fill="x", pady=(T.GAP, 0))
        self.pager = W.Paginator(self.table.footer, self.load_page, page_size=8)
        self.pager.pack(fill="x", pady=(6, 0))

        self.stats = W.transparent(self)
        self.stats.pack(fill="x", pady=(T.GAP, 0))
        W.grid_columns(self.stats, 3)
        self.reload()

    # ----------------------------------------------------------------- build
    def _build_filters(self, master):
        c = W.card(master)
        self.search = W.SearchEntry(c, _("Search by employee name, ID, or work email..."),
                                    on_change=lambda _t: self._search_later(), height=42)
        self.search.pack(fill="x", padx=16, pady=(16, 10))
        row = W.transparent(c)
        row.pack(fill="x", padx=16)
        self.dept_menu = W.option_menu(row, [self.all_depts], command=self._dept_changed, width=200)
        self.dept_menu.pack(side="left", padx=(0, 8))
        self.pos_menu = W.option_menu(row, [self.all_roles], command=lambda _v: self._filter_changed(), width=200)
        self.pos_menu.pack(side="left", padx=(0, 8))
        self.status_menu = W.option_menu(row, [self.all_status] + list(self.status_names.values()),
                                         command=lambda _v: self._filter_changed(), width=150)
        self.status_menu.pack(side="left", padx=(0, 8))
        W.button(row, _("Reset"), "ghost", "refresh", self.reset_filters, height=34, size=12).pack(side="left")
        self.showing = W.label(c, "", size=12, color=T.TEXT_2)
        self.showing.pack(anchor="w", padx=16, pady=(10, 14))
        return c

    def _columns(self):
        return [
            {"key": "code", "title": _("Emp ID"), "weight": 9,
             "render": lambda m, r: W.tag(m, r["code"], "neutral", mono=True)},
            {"key": "full_name", "title": _("Full Name"), "weight": 21,
             "render": lambda m, r: W.person_cell(m, r["first_name"], r["last_name"],
                                                  f"{labels.show(labels.EMPLOYMENT, r['employment'])} • "
                                                  f"{labels.show(labels.WORK_MODE, r['work_mode'])}")},
            {"key": "department", "title": _("Department"), "weight": 14,
             "render": lambda m, r: W.dot_text(m, r["department"],
                                               T.CATEGORY[(r["department_id"] - 1) % len(T.CATEGORY)])},
            {"key": "position", "title": _("Position / Role"), "weight": 15,
             "render": lambda m, r: W.label(m, r["position"], size=13, wraplength=125, justify="left")},
            {"key": "email", "title": _("Work Email"), "weight": 16,
             "render": lambda m, r: W.label(m, r["email"], size=12, color=T.TEXT_2)},
            {"key": "status", "title": _("Status"), "weight": 10,
             "render": lambda m, r: W.badge(m, labels.show(labels.EMPLOYEE_STATUS, r["status"]),
                                            STATUS_KIND.get(r["status"], "neutral"))},
            {"key": "actions", "title": _("Actions"), "weight": 14, "anchor": "e", "render": self._actions},
        ]

    def _actions(self, master, row):
        box = W.transparent(master)
        W.icon_button(box, "view", lambda: self.view_profile(row["id"]), fallback="👁").pack(side="left", padx=2)
        W.icon_button(box, "edit", lambda: self.open_form(row["id"]), fallback="✎").pack(side="left", padx=2)
        W.icon_button(box, "delete", lambda: self.delete(row), kind="danger_soft", fallback="✕").pack(
            side="left", padx=2)
        return box

    # ----------------------------------------------------------------- data
    def reload(self):
        tasks.run(self, _load_overview, on_done=self._render_overview)
        self.load_page()

    def _render_overview(self, data: dict):
        self.departments = data["departments"]
        self.dept_menu.configure(values=[self.all_depts] + [d["name"] for d in self.departments])
        by_status = data["summary"]["by_status"]
        self.header.chip.configure(text=_("{count} Active Members").format(
            count=sum(n for s, n in by_status.items() if s != "Terminated")))
        self._render_spread(by_status.get("Probation", 0))
        self._render_stats(data["stats"], by_status)

    def _render_spread(self, probation: int):
        for w in self.spread.winfo_children():
            w.destroy()
        top = W.transparent(self.spread)
        top.pack(fill="x", padx=16, pady=(14, 4))
        W.micro(top, _("Departmental Spread")).pack(side="left")
        body = W.transparent(self.spread)
        body.pack(fill="x", padx=12)
        depts = sorted(self.departments, key=lambda d: d["headcount"], reverse=True)
        total = sum(d["headcount"] for d in depts) or 1
        colors = [T.CATEGORY[(d["id"] - 1) % len(T.CATEGORY)] for d in depts]
        W.donut_chart(body, [d["headcount"] for d in depts], colors, str(total), size=110).pack(side="left")
        legend = W.transparent(body)
        legend.pack(side="left", padx=(10, 0))
        top3 = depts[:3]
        items = [(d["name"].split(" &")[0], d["headcount"], colors[i]) for i, d in enumerate(top3)]
        items.append((_("Others"), total - sum(d["headcount"] for d in top3), T.TEXT_3))
        for name, n, color in items:
            r = W.transparent(legend)
            r.pack(anchor="w", pady=1)
            ctk.CTkLabel(r, text="●", text_color=color, font=T.font(10), width=12).pack(side="left")
            W.label(r, f"{name}: {n} ({n / total * 100:.0f}%)", size=12, weight="semibold").pack(side="left", padx=4)
        W.label(self.spread, _("On probation: {count}").format(count=probation), size=12, color=T.TEXT_2).pack(
            anchor="w", padx=16, pady=(4, 14))

    def _render_stats(self, stats: dict, by_status: dict):
        for w in self.stats.winfo_children():
            w.destroy()
        items = [
            ("location", "success", f"{stats['present']} / {stats['expected']}", _("Clocked in today")),
            ("calendar", "info", _("{count} On Leave").format(count=by_status.get("On Leave", 0)),
             _("Employees with status 'On Leave'")),
            ("add_person", "neutral", _("{count} On Probation").format(count=by_status.get("Probation", 0)),
             _("New hires still on probation")),
        ]
        for i, (ic, kind, title, sub) in enumerate(items):
            c = W.card(self.stats)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))
            W.icon_tile(c, ic, kind, size=46, icon_size=20).pack(side="left", padx=(16, 14), pady=16)
            box = W.transparent(c)
            box.pack(side="left")
            W.label(box, title, size=20, weight="bold").pack(anchor="w")
            W.label(box, sub, size=12, color=T.TEXT_2).pack(anchor="w")

    def _filters(self) -> dict:
        dept = next((d["id"] for d in self.departments if d["name"] == self.dept_menu.get()), None)
        position = self.pos_menu.get()
        status = next((k for k, v in self.status_names.items() if v == self.status_menu.get()), None)
        return {"search": self.search.get().strip() or None, "department_id": dept,
                "position": None if position == self.all_roles else position, "status": status}

    def load_page(self):
        self.table.set_loading()
        tasks.run(self, api.employees_page, **self._filters(), limit=self.pager.limit, offset=self.pager.offset,
                  on_done=self._render_page)

    def _render_page(self, page):
        self.table.set_rows(page.rows)
        self.pager.update(page.total, len(page.rows))
        start = self.pager.offset
        self.showing.configure(text=_("Showing {start}-{end} of {total} employees").format(
            start=start + 1 if page.total else 0, end=start + len(page.rows), total=page.total))

    def _search_later(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(SEARCH_DELAY_MS, self._filter_changed)

    def _filter_changed(self):
        self._search_job = None
        self.pager.reset()
        self.load_page()

    def _dept_changed(self, name: str, refresh: bool = True):
        dept_id = next((d["id"] for d in self.departments if d["name"] == name), None)
        self.pos_menu.set(self.all_roles)

        def show_positions(positions):
            self.pos_menu.configure(values=[self.all_roles] + [p["title"] for p in positions])
        if dept_id:
            tasks.run(self, api.get_positions, dept_id, on_done=show_positions)
        else:
            self.pos_menu.configure(values=[self.all_roles])
        if refresh:
            self._filter_changed()

    def reset_filters(self):
        self.search.set("")
        self.dept_menu.set(self.all_depts)
        self._dept_changed(self.all_depts, refresh=False)
        self.status_menu.set(self.all_status)
        self._filter_changed()

    def on_show(self, search=None, add=False, **_kw):
        if search is not None:
            self.search.set(search)
            self._filter_changed()
        if add:
            self.after(100, self.open_form)

    def _changed(self):
        self.reload()
        self.app.invalidate("dashboard", "departments", "attendance", "leave", "payroll")

    # -------------------------------------------------------------- actions
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"employees_{date.today():%Y%m%d}.csv")
        if path:
            tasks.run(self, api.employees_page, **self._filters(), on_done=lambda page: self._write_csv(path, page))

    def _write_csv(self, path, page):
        cols = ["code", "first_name", "last_name", "email", "phone", "gender", "department", "position", "salary",
                "hire_date", "status", "employment", "work_mode"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(page.rows)
        W.toast(self, _("Exported {count} employees to CSV").format(count=len(page.rows)))

    def delete(self, e: dict):
        if not W.confirm(self, _("Delete Employee"),
                         _("Permanently remove {name} ({code}) from the directory?\n"
                           "Attendance, leave and payroll history will no longer be shown.").format(
                             name=e["full_name"], code=e["code"]), ok_text=_("Delete")):
            return

        def deleted(_result):
            self._changed()
            W.toast(self, _("{name} was removed").format(name=e["full_name"]), "danger")
        tasks.run(self, api.delete_employee, e["id"], on_done=deleted)

    def view_profile(self, emp_id: int):
        tasks.run(self, api.get_employee, emp_id, on_done=self._profile)

    def _profile(self, e: dict):
        dlg = W.Modal(self, e["full_name"], f"{e['code']} • {e['position']}", width=560, height=600)
        head = W.transparent(dlg.body)
        head.pack(fill="x", padx=12, pady=(8, 12))
        W.avatar(head, e["first_name"], e["last_name"], size=64).pack(side="left")
        box = W.transparent(head)
        box.pack(side="left", padx=14)
        W.label(box, e["full_name"], size=18, weight="bold").pack(anchor="w")
        W.label(box, f"{e['department']} • {labels.show(labels.WORK_MODE, e['work_mode'])}", size=12,
                color=T.TEXT_2).pack(anchor="w")
        W.badge(box, labels.show(labels.EMPLOYEE_STATUS, e["status"]), STATUS_KIND.get(e["status"], "neutral")).pack(
            anchor="w", pady=(6, 0))
        grid = W.card(dlg.body, fg=T.SURFACE_ALT)
        grid.pack(fill="x", padx=12, pady=4)
        grid.grid_columnconfigure((0, 1), weight=1, uniform="p")
        fields = [(_("Work Email"), e["email"]), (_("Phone"), e["phone"] or "-"),
                  (_("Gender"), labels.show(labels.GENDER, e["gender"])),
                  (_("Hire Date"), i18n.format_date(e["hire_date"])),
                  (_("Employment"), labels.show(labels.EMPLOYMENT, e["employment"])),
                  (_("Shift"), labels.show(labels.SHIFT, e["shift"])),
                  (_("Base Salary"), _("{amount} / month").format(amount=W.money(e["salary"]))),
                  (_("Department"), e["department"])]
        for i, (k, v) in enumerate(fields):
            cell = W.transparent(grid)
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=16, pady=8)
            W.micro(cell, k).pack(anchor="w")
            W.label(cell, v, size=13, weight="semibold").pack(anchor="w")
        dlg.add_button(_("Edit Profile"), "primary", lambda: (dlg.destroy(), self.open_form(e["id"])), "edit")
        dlg.add_button(_("Close"), "secondary", dlg.destroy)

    def open_form(self, emp_id: int | None = None):
        if not self.departments:
            W.toast(self, _("Still loading, please try again in a moment."), "info")
            return

        def load():
            emp = api.get_employee(emp_id) if emp_id else {}
            dept_id = emp.get("department_id", self.departments[0]["id"])
            return emp, api.get_positions(dept_id)
        tasks.run(self, load, on_done=lambda result: self._form(emp_id, *result))

    def _form(self, emp_id, e: dict, positions: list[dict]):
        dlg = W.Modal(self, _("Edit Employee") if emp_id else _("Add Employee"), _("Fields marked * are required"),
                      width=580, height=700)
        f = W.Form(dlg.body)
        f.entry("first_name", _("First Name *"), e.get("first_name", ""), _("e.g. Jane"))
        f.entry("last_name", _("Last Name *"), e.get("last_name", ""), _("e.g. Doe"))
        f.entry("email", _("Work Email *"), e.get("email", ""), "name@workflow.io", span=2)
        f.entry("phone", _("Phone"), e.get("phone", ""), "+855 12 345 678")
        f.option("gender", _("Gender"), list(labels.GENDER), e.get("gender", "Male"),
                 labels=labels.choices(labels.GENDER))
        f.entry("hire_date", _("Hire Date * (YYYY-MM-DD)"), e.get("hire_date", date.today().isoformat()))
        f.entry("salary", _("Base Salary (per month) *"), e.get("salary", ""), _("e.g. 4500"))

        names = [d["name"] for d in self.departments]
        current = e.get("department", names[0])
        titles = [p["title"] for p in positions] or ["-"]
        pos_menu: dict = {}

        def dept_changed(name):
            dept_id = next(d["id"] for d in self.departments if d["name"] == name)

            def show(new_positions):
                new_titles = [p["title"] for p in new_positions] or ["-"]
                pos_menu["w"].configure(values=new_titles)
                f.fields["position"][1].set(new_titles[0])
            tasks.run(dlg, api.get_positions, dept_id, on_done=show)

        f.option("department", _("Department *"), names, current, command=dept_changed)
        pos_menu["w"] = f.option("position", _("Position *"), titles, e.get("position", titles[0]))
        statuses = {k: v for k, v in labels.EMPLOYEE_STATUS.items() if k != "Terminated"}
        f.option("status", _("Status"), list(statuses), e.get("status", "Probation"), labels=labels.choices(statuses))
        f.option("employment", _("Employment"), list(labels.EMPLOYMENT), e.get("employment", "Full-time"),
                 labels=labels.choices(labels.EMPLOYMENT))
        f.option("work_mode", _("Work Mode"), list(labels.WORK_MODE), e.get("work_mode", "HQ Onsite"),
                 labels=labels.choices(labels.WORK_MODE))
        f.option("role", _("System Role"), list(labels.ROLE), e.get("role") or "Employee",
                 labels=labels.choices(labels.ROLE))
        error = W.label(dlg.body, "", size=12, color=T.DANGER, wraplength=500, justify="left")
        error.pack(anchor="w", padx=20, pady=(4, 0))

        def saved(result: dict):
            dlg.destroy()
            self._changed()
            name = f"{result['first_name']} {result['last_name']}"
            if result.get("username"):  # new account created by the backend
                W.info_dialog(self, _("Employee Added"),
                              _("{name} was added.\n\nLogin username:  {username}\nInitial password:  {password}\n\n"
                                "Share these with the employee and ask them to change the password.").format(
                                  name=name, username=result["username"], password=result["initial_password"]),
                              height=320)
            else:
                W.toast(self, _("{name} saved").format(name=name))

        def failed(err: Exception):
            if not isinstance(err, ApiError):
                raise err
            error.configure(text=str(err))

        def save():
            values = f.values()
            dept_id = next(d["id"] for d in self.departments if d["name"] == values["department"])
            data, problem = forms.employee(values, dept_id)
            if problem:
                error.configure(text=problem)
                return
            call = (lambda: api.update_employee(emp_id, data)) if emp_id else (lambda: api.create_employee(data))
            tasks.run(dlg, call, on_done=saved, on_error=failed)

        dlg.add_button(_("Save Employee"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
