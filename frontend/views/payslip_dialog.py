"""Payroll dialogs: the payslip (save as PDF, email) and editing a line's bonus / adjustment."""
from tkinter import filedialog

import customtkinter as ctk

from core import tasks
from core.api_client import ApiError, api
from core.i18n import _
from core.state import state
from logic import forms, labels
from logic.formatting import month_label
from ui import theme as T
from ui import widgets as W
from ui.icons import logo

STATUS_KIND = {"Calculated": "info", "Paid": "success", "Pending": "neutral"}


class PayslipDialogs:
    """Payroll dialogs: the payslip (save as PDF, email) and editing a line's bonus / adjustment."""

    def edit_line(self, r, on_saved):
        """Bonus, adjustment (+ earning / - deduction) and note of an unpaid line."""
        dlg = W.Modal(self, _("Edit Bonus / Adjustment"), f"{r['employee']} • {month_label(r['month'])}",
                      width=480, height=420, scroll=False)
        f = W.Form(dlg.body)
        f.entry("bonus", _("Allowances / Bonus"), f"{r['bonus']:g}")
        f.entry("adjustment", _("Adjustment (+ / -)"), f"{r['adjustment']:g}", _("e.g. -50"))
        f.entry("note", _("Note"), r.get("note", ""), _("e.g. advance repaid"), span=2)
        error = W.label(dlg.body, "", size=12, color=T.DANGER, wraplength=420, justify="left")
        error.pack(anchor="w", padx=20, pady=(4, 0))

        def failed(err: Exception):
            if not isinstance(err, ApiError):
                raise err
            error.configure(text=str(err))

        def saved(line):
            dlg.destroy()
            self.reload()
            W.toast(self, _("Payroll line updated"))
            on_saved(line)

        def save():
            data, problem = forms.payroll_line(f.values())
            if problem:
                error.configure(text=problem)
                return
            tasks.run(dlg, api.update_payroll_line, r["id"], data, on_done=saved, on_error=failed)
        dlg.add_button(_("Save"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)

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
        facts = [(_("Employee"), r["employee"]), (_("Employee ID"), r["code"]),
                 (_("Department"), r["department"]), (_("Pay Period"), month_label(r["month"]))]
        if r.get("paid_days"):
            facts.append((_("Paid Days"), _("{days} of {total}").format(days=r["paid_days"], total=r["month_days"])))
        if r.get("note"):
            facts.append((_("Note"), r["note"]))
        for i, (k, v) in enumerate(facts):
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

        earnings = [(_("Base Salary"), r["base_salary"])]
        if r.get("overtime_pay"):
            earnings.append((_("Overtime ({hours:g} h)").format(hours=r["overtime_hours"]), r["overtime_pay"]))
        earnings.append((_("Allowances / Bonus"), r["bonus"]))
        if r.get("adjustment"):
            earnings.append((_("Adjustment"), r["adjustment"]))
        gross = r["base_salary"] + r.get("overtime_pay", 0) + r["bonus"] + r.get("adjustment", 0)
        section(_("Earnings"), earnings, _("Gross Earnings"), gross, T.SUCCESS)
        tax_label = (_("Income Tax (progressive)") if s.get("tax_brackets")
                     else _("Income Tax ({rate}%)").format(rate=round(s.get("tax_rate", 0))))
        deductions = [(tax_label, r["tax"]),
                      (_("Pension ({rate}%)").format(rate=round(s.get("pension_rate", 0))), r["pension"]),
                      (_("Health Insurance"), r["insurance"])]
        if r.get("unpaid_deduction"):
            deductions.insert(0, (_("Unpaid Days ({days:g})").format(days=r["unpaid_days"]), r["unpaid_deduction"]))
        section(_("Deductions"), deductions, _("Total Deductions"), r["deductions"], T.DANGER)

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
        if self.staff and r["status"] != "Paid":
            def reopen(line):
                dlg.destroy()
                self.payslip(line)
            dlg.add_button(_("Edit"), "secondary", lambda: self.edit_line(r, reopen), "edit")
