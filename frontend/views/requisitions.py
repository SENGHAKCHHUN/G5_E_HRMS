"""Departments screen: the open requisitions panel and the new requisition form."""
import customtkinter as ctk

from core import i18n, tasks
from core.api_client import api
from core.i18n import _
from logic import labels
from ui import theme as T
from ui import widgets as W
from views.common import submit


class RequisitionPanel:
    """Departments screen: the open requisitions panel and the new requisition form."""

    def _render_requisitions(self, d, positions, reqs):
        c = W.card(self.detail)
        c.pack(fill="x", pady=(T.GAP, 0))
        head = W.transparent(c)
        head.pack(fill="x", padx=18, pady=14)
        W.section_title(head, _("Open Requisitions"),
                        chip=_("{count} openings").format(count=sum(r["openings"] for r in reqs))).pack(side="left")
        W.button(head, _("New Requisition"), "ghost", "add", lambda: self.requisition_form(d, positions), height=30,
                 size=12).pack(side="right")
        if not reqs:
            W.label(c, _("No open hiring requests for this department."), size=12, color=T.TEXT_2).pack(
                anchor="w", padx=18, pady=(0, 16))
            return
        for r in reqs:
            row = ctk.CTkFrame(c, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
            row.pack(fill="x", padx=18, pady=(0, 6))
            W.tag(row, r["code"], "info", mono=True).pack(side="left", padx=12, pady=10)
            opened = _("Opened {date} by {user}").format(date=i18n.format_date(r["created_at"]), user=r["created_by"])
            note = f" · {r['note']}" if r["note"] else ""
            W.cell_stack(row, f"{r['openings']} × {r['title']}", opened + note).pack(
                side="left")
            W.button(row, _("Cancel"), "danger_soft", command=lambda x=r: self._close_requisition(x, "Cancelled"),
                     height=28, size=11).pack(side="right", padx=(4, 12))
            W.button(row, _("Mark Filled"), "success", "check", lambda x=r: self._close_requisition(x, "Filled"),
                     height=28, size=11).pack(side="right")
        ctk.CTkFrame(c, height=10, fg_color="transparent").pack()

    def _close_requisition(self, r, status):
        def done(_result):
            self._load_detail()
            W.toast(self, _("{code} marked {status}").format(code=r["code"],
                                                             status=labels.show(labels.REQUISITION_STATUS, status)),
                    "success" if status == "Filled" else "warning")
        tasks.run(self, api.update_requisition, r["id"], status, on_done=done)

    def requisition_form(self, d, positions, role=None, openings=1):
        titles = [p["title"] for p in positions] or ["-"]
        dlg = W.Modal(self, _("Create Requisition"), _("Request to hire for {department}").format(department=d["name"]),
                      height=460)
        f = W.Form(dlg.body)
        f.option("position", _("Job Role *"), titles, role["title"] if role else titles[0], span=2)
        f.entry("openings", _("Openings *"), openings)
        f.textbox("note", _("Note for recruitment"), height=80)
        err = W.label(dlg.body, "", size=12, color=T.DANGER)
        err.pack(anchor="w", padx=20)

        def done(req):
            dlg.destroy()
            self._load_detail()
            W.toast(self, _("{code} opened: {count} × {title}").format(code=req["code"], count=req["openings"],
                                                                        title=req["title"]))

        def save():
            v = f.values()
            pos = next((p for p in positions if p["title"] == v["position"]), None)
            if not v["openings"].isdigit() or int(v["openings"]) < 1:
                err.configure(text=_("Openings must be a number."))
                return
            data = {"department_id": d["id"], "position_id": pos["id"] if pos else None, "title": v["position"],
                    "openings": int(v["openings"]), "note": v["note"]}
            submit(dlg, lambda: api.create_requisition(data), err, done)

        dlg.add_button(_("Create"), "primary", save, "check")
        dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
