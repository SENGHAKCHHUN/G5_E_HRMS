"""Departments screen dialogs: staff in a position, delete position, department and position forms."""
import customtkinter as ctk

from core import tasks
from core.api_client import api
from core.i18n import _
from logic import forms, labels
from ui import theme as T
from ui import widgets as W
from views.common import submit


class DepartmentDialogs:
    """Departments screen dialogs: staff in a position, delete position, department and position forms."""

    def view_staff(self, pos):
        tasks.run(self, api.employees_page, department_id=pos["department_id"], position=pos["title"],
                  on_done=lambda page: self._staff_dialog(pos, page.rows))

    def _staff_dialog(self, pos, staff):
        dlg = W.Modal(self, pos["title"], _("{count} employees • Grade {grade}").format(count=len(staff),
                                                                                        grade=pos["grade"]),
                      height=560)
        if not staff:
            W.label(dlg.body, _("No employees assigned to this role yet."), color=T.TEXT_2).pack(pady=30)
        for e in staff:
            item = ctk.CTkFrame(dlg.body, fg_color=T.SURFACE_ALT, corner_radius=T.RADIUS_BTN)
            item.pack(fill="x", padx=8, pady=3)
            W.person_cell(item, e["first_name"], e["last_name"], f"{e['code']} • {e['email']}").pack(
                side="left", padx=10, pady=8)
            W.badge(item, labels.show(labels.EMPLOYEE_STATUS, e["status"]),
                    {"Active": "success", "Probation": "info"}.get(e["status"], "neutral")).pack(side="right", padx=10)
        dlg.add_button(_("Close"), "primary", dlg.destroy)

    def delete_position(self, pos):
        if pos["headcount"]:
            W.toast(self, _("Reassign the {count} employees in this role before deleting it").format(
                count=pos["headcount"]), "warning")
            return
        if W.confirm(self, _("Delete Job Role"), _("Delete the role '{title}'?").format(title=pos["title"]),
                     ok_text=_("Delete")):
            def done(_result):
                self._changed()
                W.toast(self, _("Job role deleted"), "danger")
            tasks.run(self, api.delete_position, pos["id"], on_done=done)

    def department_form(self, d=None):
        d = d or {}
        dlg = W.Modal(self, _("Edit Department") if d else _("New Department"),
                      _("Department profile and staffing target"), height=580)
        f = W.Form(dlg.body)
        f.entry("name", _("Department Name *"), d.get("name", ""), _("e.g. Customer Success"), span=2)
        f.entry("lead", _("Department Lead"), d.get("lead", ""), _("Full name"))
        f.entry("location", _("Location"), d.get("location", ""), _("e.g. HQ Floor 2"))
        f.entry("budget", _("Monthly Budget"), d.get("budget", ""), _("e.g. 120000"))
        f.entry("target", _("Headcount Target"), d.get("target", ""), _("e.g. 12"))
        f.textbox("description", _("Description"), d.get("description", ""))
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)

        def done(result):
            if not d:
                self.selected = result["id"]
            dlg.destroy()
            self._changed()
            W.toast(self, _("Department '{name}' saved").format(name=result["name"]))

        def save():
            data, problem = forms.department(f.values())
            if problem:
                err.configure(text=problem)
                return
            call = (lambda: api.update_department(d["id"], data)) if d else (lambda: api.create_department(data))
            submit(dlg, call, err, done)

        dlg.add_button(_("Save Department"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)

    def position_form(self, pos=None, dept_id=None):
        if not self.departments:
            return
        pos = pos or {}
        names = [d["name"] for d in self.departments]
        current = next((d["name"] for d in self.departments
                        if d["id"] == (pos.get("department_id") or dept_id or self.selected)), names[0])
        dlg = W.Modal(self, _("Edit Job Role") if pos else _("New Job Role"), _("Position title, pay grade and range"),
                      height=580)
        f = W.Form(dlg.body)
        f.option("department", _("Department *"), names, current, span=2)
        f.entry("title", _("Position Title *"), pos.get("title", ""), _("e.g. Data Engineer"), span=2)
        f.entry("grade", _("Pay Grade *"), pos.get("grade", ""), _("e.g. E-3"))
        f.entry("planned", _("Planned Headcount"), pos.get("planned", ""), _("e.g. 4"))
        f.entry("min_salary", _("Min Salary (per month) *"), pos.get("min_salary", ""), _("e.g. 4000"))
        f.entry("max_salary", _("Max Salary (per month) *"), pos.get("max_salary", ""), _("e.g. 5500"))
        f.entry("skills", _("Key Skills"), pos.get("skills", ""), _("e.g. Python, SQL, Airflow"), span=2)
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)

        def done(result):
            self.selected = result["department_id"]
            dlg.destroy()
            self._changed()
            W.toast(self, _("Job role '{title}' saved").format(title=result["title"]))

        def save():
            values = f.values()
            department_id = next(d["id"] for d in self.departments if d["name"] == values["department"])
            data, problem = forms.position(values, department_id)
            if problem:
                err.configure(text=problem)
                return
            call = (lambda: api.update_position(pos["id"], data)) if pos else (lambda: api.create_position(data))
            submit(dlg, call, err, done)

        dlg.add_button(_("Save Role"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
