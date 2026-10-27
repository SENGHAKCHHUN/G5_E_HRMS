"""Screen 5 - Departments & Positions (Module 3)."""
import customtkinter as ctk

from core import tasks
from core.api_client import api
from core.i18n import _
from ui import theme as T
from ui import widgets as W
from views.department_dialogs import DepartmentDialogs
from views.requisitions import RequisitionPanel


def _load_detail(dept_id: int) -> dict:
    return {"positions": api.get_positions(dept_id),
            "requisitions": api.get_requisitions(department_id=dept_id, status="Open")}


def _load_overview() -> dict:
    return {"departments": api.get_departments(), "roles": len(api.get_positions())}


class DepartmentView(RequisitionPanel, DepartmentDialogs, ctk.CTkFrame):
    """Department list and detail. The requisitions panel is in views/requisitions.py, the dialogs
    (staff, department and position forms) in views/department_dialogs.py."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.departments: list[dict] = []
        self.selected: int | None = None
        self.query = ""

        self.header = W.PageHeader(self, _("Departments & Positions"), _("Loading..."),
                                   chip=_("Organization Structure"), icon_name="org")
        self.header.pack(fill="x")
        self.header.add_action(_("Add Job Role"), "secondary", "add", lambda: self.position_form())
        self.header.add_action(_("Add Department"), "primary", "add", lambda: self.department_form())

        body = W.transparent(self)
        body.pack(fill="both", expand=True, pady=(T.GAP, 0))
        body.grid_columnconfigure(0, weight=10, uniform="dep")
        body.grid_columnconfigure(1, weight=22, uniform="dep")

        left = W.card(body)
        left.grid(row=0, column=0, sticky="new", padx=(0, 8))
        W.SearchEntry(left, _("Search departments or heads..."), on_change=self._search, width=300).pack(
            fill="x", padx=12, pady=(12, 8))
        self.dept_list = W.transparent(left)
        self.dept_list.pack(fill="x", padx=12)
        self.budget = ctk.CTkFrame(left, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        self.budget.pack(fill="x", padx=12, pady=12)

        self.detail = W.transparent(body)
        self.detail.grid(row=0, column=1, sticky="new", padx=(8, 0))
        self.reload()

    # ------------------------------------------------------------------ data
    def reload(self):
        tasks.run(self, _load_overview, on_done=self._render_overview)

    def _render_overview(self, data: dict):
        self.departments = data["departments"]
        if self.selected not in {d["id"] for d in self.departments}:
            self.selected = self.departments[0]["id"] if self.departments else None
        self.header.subtitle.configure(text="●  " + _("{departments} departments  ·  {roles} job roles").format(
            departments=len(self.departments), roles=data["roles"]))
        self._render_list()
        self._load_detail()

    def _search(self, text: str):
        self.query = text.strip().lower()
        self._render_list()

    def select(self, dept_id: int):
        self.selected = dept_id
        self._render_list()
        self._load_detail()

    def _changed(self):
        self.reload()
        self.app.invalidate("dashboard", "employees", "payroll")

    def _department(self) -> dict | None:
        return next((x for x in self.departments if x["id"] == self.selected), None)

    # ------------------------------------------------------------- left list
    def _render_list(self):
        for w in self.dept_list.winfo_children():
            w.destroy()
        for d in self.departments:
            if self.query and self.query not in f"{d['name']} {d['lead']}".lower():
                continue
            active = d["id"] == self.selected
            item = ctk.CTkFrame(self.dept_list, corner_radius=T.RADIUS_BTN,
                                fg_color=T.PRIMARY_SOFT if active else T.SURFACE_ALT, border_width=1,
                                border_color=T.PRIMARY if active else T.BORDER)
            item.pack(fill="x", pady=4)
            top = W.transparent(item)
            top.pack(fill="x", padx=12, pady=(10, 0))
            W.icon_tile(top, d.get("icon", "department"), "info" if active else "neutral", size=34,
                        icon_size=16).pack(side="left")
            names = W.transparent(top)
            names.pack(side="left", padx=10)
            W.label(names, d["name"], size=14, weight="semibold").pack(anchor="w")
            W.label(names, _("Lead: {name}").format(name=d["lead"]), size=11, color=T.TEXT_2).pack(anchor="w")
            W.tag(top, _("{count} Members").format(count=d["headcount"]), "info" if active else "neutral").pack(
                side="right", anchor="n")
            bottom = W.transparent(item)
            bottom.pack(fill="x", padx=12, pady=(6, 10))
            W.label(bottom, _("{count} Roles").format(count=d["roles"]), size=12, color=T.TEXT_2).pack(side="left")
            if d["target"]:
                W.label(bottom, _("Target {count}").format(count=d["target"]), size=12, color=T.TEXT_2).pack(
                    side="right")
            W.make_clickable(item, lambda i=d["id"]: self.select(i))

        for w in self.budget.winfo_children():
            w.destroy()
        total = sum(d["budget"] for d in self.departments)
        staffed = sum(d["headcount"] for d in self.departments)
        target = sum(d["target"] for d in self.departments)
        W.label(self.budget, _("Total budget: {amount}/mo").format(amount=W.money(total)), size=13,
                weight="semibold").pack(side="left", padx=12, pady=12)
        if target:
            W.label(self.budget, "● " + _("{percent}% staffed").format(percent=round(staffed / target * 100)),
                    size=12, weight="semibold", color=T.SUCCESS).pack(side="right", padx=12)

    # ----------------------------------------------------------- right side
    def _load_detail(self):
        if self.selected is None:
            return
        for w in self.detail.winfo_children():
            w.destroy()
        W.label(self.detail, _("Loading..."), color=T.TEXT_3).pack(pady=40)
        tasks.run(self, _load_detail, self.selected, on_done=self._render_detail)

    def _render_detail(self, data: dict):
        for w in self.detail.winfo_children():
            w.destroy()
        d = self._department()
        if d is None:
            W.label(self.detail, _("No department selected"), color=T.TEXT_2).pack(pady=40)
            return
        positions = data["positions"]

        info = W.card(self.detail)
        info.pack(fill="x")
        top = W.transparent(info)
        top.pack(fill="x", padx=18, pady=(16, 10))
        W.icon_tile(top, d.get("icon", "department"), "info", size=48, icon_size=22).pack(side="left")
        names = W.transparent(top)
        names.pack(side="left", padx=12)
        row = W.transparent(names)
        row.pack(anchor="w")
        W.label(row, d["name"], size=20, weight="bold").pack(side="left")
        W.tag(row, d["code"], "info").pack(side="left", padx=10)
        W.label(names, _("Lead: {lead}   •   Location: {location}").format(lead=d["lead"], location=d["location"]),
                size=12, color=T.TEXT_2).pack(anchor="w")
        W.button(top, _("Edit Department"), "secondary", "edit", lambda: self.department_form(d), height=34,
                 size=12).pack(side="right")

        tiles = W.transparent(info)
        tiles.pack(fill="x", padx=18, pady=(0, 18))
        W.grid_columns(tiles, 3, uniform="tiles")
        self._tile(tiles, 0, _("Monthly Salaries"), W.money(d["payroll"]),
                   _("Average {amount}").format(amount=W.money(d["avg_salary"])))
        t = self._tile(tiles, 1, _("Headcount"), str(d["headcount"]),
                       _("Target {count}").format(count=d["target"]) if d["target"] else "")
        if d["target"]:
            W.progress(t, d["headcount"] / d["target"]).pack(fill="x", padx=14, pady=(0, 14))
        self._tile(tiles, 2, _("Avg. Seniority"), _("{years} years").format(years=d["avg_seniority"]),
                   _("Calculated from hire dates"))

        roles = W.card(self.detail)
        roles.pack(fill="x", pady=(T.GAP, 0))
        head = W.transparent(roles)
        head.pack(fill="x", padx=18, pady=14)
        W.section_title(head, _("Job Roles"), chip=_("{count} roles").format(count=len(positions))).pack(side="left")
        W.button(head, _("Add Role"), "ghost", "add", lambda: self.position_form(dept_id=d["id"]), height=30,
                 size=12).pack(side="right")
        table = W.DataTable(roles, [
            {"key": "title", "title": _("Position Title"), "weight": 21,
             "render": lambda m, r: W.cell_stack(m, r["title"], r["skills"])},
            {"key": "grade", "title": _("Pay Grade"), "weight": 10,
             "render": lambda m, r: W.tag(m, _("Grade {grade}").format(grade=r["grade"]), "info")},
            {"key": "range", "title": _("Base Range"), "weight": 16,
             "render": lambda m, r: W.label(m, _("{low} - {high} /mo").format(low=W.money(r["min_salary"]),
                                                                              high=W.money(r["max_salary"])),
                                            size=12, weight="semibold")},
            {"key": "headcount", "title": _("Headcount"), "weight": 12,
             "render": lambda m, r: W.label(m, _("{count} staff").format(count=r["headcount"]), size=13)},
            {"key": "actions", "title": _("Actions"), "weight": 20, "anchor": "e", "render": self._role_actions},
        ], empty_text=_("No job roles defined yet"), row_height=60)
        table.configure(border_width=0, fg_color="transparent")
        table.pack(fill="x", pady=(0, 4))
        table.set_rows(positions)
        W.label(roles, _("{roles} roles  ·  {people} people").format(
            roles=len(positions), people=sum(p["headcount"] for p in positions)), size=12, color=T.TEXT_2).pack(
            anchor="w", padx=18, pady=(0, 14))

        gap = d["target"] - d["headcount"]
        if gap > 0 and positions:
            role = max(positions, key=lambda p: p["planned"] - p["headcount"])
            v = W.card(self.detail)
            v.pack(fill="x", pady=(T.GAP, 0))
            W.icon_tile(v, "add_person", "success", size=44, icon_size=20).pack(side="left", padx=16, pady=16)
            box = W.transparent(v)
            box.pack(side="left", fill="x", expand=True)
            W.label(box, _("{count} below the headcount target").format(count=gap), size=15,
                    weight="semibold").pack(anchor="w")
            W.label(box, _("Most unfilled planned seats: {title}").format(title=role["title"]), size=12,
                    color=T.TEXT_2).pack(anchor="w")
            W.button(v, _("Create Requisition"), "soft", "add", lambda: self.requisition_form(d, positions, role, gap),
                     height=34, size=12).pack(side="right", padx=16)
        self._render_requisitions(d, positions, data["requisitions"])

    def _tile(self, master, col, title, value, foot):
        t = ctk.CTkFrame(master, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        t.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0 if col == 2 else 6))
        W.micro(t, title).pack(anchor="w", padx=14, pady=(12, 0))
        W.label(t, value, size=22, weight="bold").pack(anchor="w", padx=14)
        if foot:
            W.label(t, foot, size=12, color=T.TEXT_2).pack(anchor="w", padx=14, pady=(0, 12))
        return t

    def _role_actions(self, master, row):
        box = W.transparent(master)
        W.button(box, _("View Staff"), "secondary", command=lambda: self.view_staff(row), height=30, size=12).pack(
            side="left", padx=2)
        W.icon_button(box, "edit", lambda: self.position_form(row), size=30, fallback="✎").pack(side="left", padx=2)
        W.icon_button(box, "delete", lambda: self.delete_position(row), kind="danger_soft", size=30,
                      fallback="✕").pack(side="left", padx=2)
        return box
