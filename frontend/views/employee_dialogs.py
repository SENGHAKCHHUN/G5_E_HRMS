"""Employee Directory dialogs: profile, add / edit form, and the new account's sign-in details."""
from datetime import date

from core import i18n, tasks
from core.api_client import ApiError, api
from core.i18n import _
from logic import forms, labels
from ui import theme as T
from ui import widgets as W

STATUS_KIND = {"Active": "success", "On Leave": "neutral", "Probation": "info", "Terminated": "danger"}


class EmployeeDialogs:
    """Employee Directory dialogs: profile, add / edit form, and the new account's sign-in details."""

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
        # a new hire cannot start as Terminated; an existing one is terminated here (payroll pays to the last day)
        statuses = {k: v for k, v in labels.EMPLOYEE_STATUS.items() if emp_id or k != "Terminated"}
        f.option("status", _("Status"), list(statuses), e.get("status", "Probation"), labels=labels.choices(statuses))
        if emp_id:
            f.entry("termination_date", _("Last Working Day (YYYY-MM-DD, if Terminated)"),
                    e.get("termination_date") or "", _("empty = today"))
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
                self._show_new_login(name, result["username"], result["initial_password"])
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

    def _show_new_login(self, name: str, username: str, password: str):
        """The new account's sign-in details. The password is shown only here, so it can be copied."""
        dlg = W.Modal(self, _("Employee Added"), _("{name} was added.").format(name=name), width=480, height=380,
                      scroll=False)
        W.label(dlg.body, _("Give these to the employee. They will be asked to choose their own password "
                            "when they sign in. This password is not shown again."), size=12, color=T.TEXT_2,
                wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(8, 10))
        details = ((_("Login username"), username), (_("Initial password"), password))
        for text, value in details:
            W.label(dlg.body, text, size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w", padx=16,
                                                                                    pady=(6, 0))
            W.label(dlg.body, value, size=18, weight="bold", mono=True, color=T.PRIMARY).pack(anchor="w", padx=16)

        def copy():
            dlg.clipboard_clear()
            dlg.clipboard_append("\n".join(f"{text}: {value}" for text, value in details))
            W.toast(dlg, _("Copied"))
        dlg.add_button(_("Done"), "primary", dlg.destroy)
        dlg.add_button(_("Copy"), "secondary", copy, "document")
