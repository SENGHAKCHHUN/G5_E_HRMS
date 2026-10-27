"""Settings section: authentication & user accounts (password reset, 2FA reset)."""
from core import tasks
from core.api_client import api
from core.i18n import _
from logic import labels
from ui import theme as T
from ui import widgets as W


class AccountSection:
    """Settings section: authentication & user accounts (password reset, 2FA reset)."""

    def _sec_auth(self):
        b = self._section(_("Security & Session Policy"), _("Role-based access control and session length"),
                          "shield", right=_("RBAC Enforced"))
        self._option(b, "jwt_hours", _("Session Expiry (hours)"), ["1", "4", "8", "12", "24"], 0, 0)
        self._toggle_row(b, "enforce_mfa", _("Enforce 2FA for staff"),
                         _("Admin & HR must use an authenticator app"), 0, 1)

        W.label(b, _("Role Permissions Overview"), size=13, weight="semibold").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(14, 6))
        perms = W.DataTable(b, [
            {"key": "role", "title": _("Role"), "weight": 10,
             "render": lambda m, r: W.dot_text(m, labels.show(labels.ROLE, r["role"]), r["color"])},
            {"key": "emp", "title": _("Employees"), "weight": 12},
            {"key": "pay", "title": _("Payroll"), "weight": 12},
            {"key": "att", "title": _("Attendance"), "weight": 12},
            {"key": "sys", "title": _("Settings"), "weight": 10},
        ], row_height=42)
        perms.grid(row=2, column=0, columnspan=2, sticky="ew")
        perms.set_rows([
            {"role": "Admin", "color": T.DANGER, "emp": _("Full (Read/Write)"), "pay": _("Full (Pay)"),
             "att": _("Full (Override)"), "sys": _("Full")},
            {"role": "HR Manager", "color": T.PRIMARY, "emp": _("Full (Read/Write)"), "pay": _("Calculate & Run"),
             "att": _("Approve / Log"), "sys": _("None")},
            {"role": "Employee", "color": T.SUCCESS, "emp": _("Own profile"), "pay": _("Own payslips"),
             "att": _("Own clock in/out"), "sys": _("None")},
        ])

        u = self._section(_("User Accounts"), _("Reset a forgotten password or a lost authenticator"), "person")
        self.users = W.DataTable(u, [
            {"key": "username", "title": _("Username"), "weight": 10,
             "render": lambda m, r: W.label(m, r["username"], size=13, weight="semibold", mono=True)},
            {"key": "role", "title": _("Role"), "weight": 9,
             "render": lambda m, r: W.badge(m, labels.show(labels.ROLE, r["role"]),
                                            {"Admin": "danger", "HR Manager": "info"}.get(r["role"], "success"))},
            {"key": "employee", "title": _("Linked Employee"), "weight": 15},
            {"key": "security", "title": _("Security"), "weight": 9, "render": self._security_cell},
            {"key": "actions", "title": _("Actions"), "weight": 15, "anchor": "e", "render": self._user_actions},
        ], row_height=48)
        self.users.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.user_pager = W.Paginator(self.users.footer, self._show_users, page_size=8)
        self.user_pager.pack(fill="x", pady=(6, 0))
        self.all_users: list[dict] = []
        self._reload_users()

    def _show_users(self):
        self.users.set_rows(self.user_pager.slice(self.all_users))

    def _reload_users(self):
        self.users.set_loading()

        def show(users):
            self.all_users = users
            if self.users.winfo_exists():
                self._show_users()
        tasks.run(self.users, api.get_users, on_done=show)

    @staticmethod
    def _security_cell(m, r):
        box = W.transparent(m)
        if r.get("totp_enabled"):
            W.badge(box, "2FA", "success").pack(side="left", padx=(0, 4))
        if r.get("must_change_password"):
            W.badge(box, _("Temp"), "warning").pack(side="left")
        if not box.winfo_children():
            W.label(box, _("Password"), size=12, color=T.TEXT_2).pack(side="left")
        return box

    def _user_actions(self, m, r):
        box = W.transparent(m)
        W.button(box, _("Reset Password"), "secondary", command=lambda: self._reset_password(r),
                 height=28, size=11).pack(side="left", padx=2)
        if r.get("totp_enabled"):
            W.button(box, _("Reset 2FA"), "danger_soft", command=lambda: self._reset_2fa(r),
                     height=28, size=11).pack(side="left", padx=2)
        return box

    def _reset_password(self, r):
        if W.confirm(self, _("Reset Password"),
                     _("Create a one-time temporary password for '{user}'?\nTheir current password stops working "
                       "and they must choose a new one at next sign-in.").format(user=r["username"]),
                     ok_text=_("Reset"), kind="primary"):
            tasks.run(self, api.reset_password, r["id"], on_done=self._show_temporary_password)

    def _show_temporary_password(self, res):
        self._reload_users()
        dlg = W.Modal(self, _("Temporary Password"), _("For {user}").format(user=res["username"]), width=460,
                      height=300, scroll=False)
        W.label(dlg.body, _("Give this password to the user. It works once; they will be asked to set "
                            "their own password when they sign in."), size=12, color=T.TEXT_2,
                wraplength=400, justify="left").pack(anchor="w", padx=16, pady=(8, 10))
        W.label(dlg.body, res["temporary_password"], size=20, weight="bold", mono=True,
                color=T.PRIMARY).pack(anchor="w", padx=16)

        def copy():
            dlg.clipboard_clear()
            dlg.clipboard_append(res["temporary_password"])
            W.toast(dlg, _("Copied"))
        dlg.add_button(_("Done"), "primary", dlg.destroy)
        dlg.add_button(_("Copy"), "secondary", copy, "document")

    def _reset_2fa(self, r):
        if not W.confirm(self, _("Reset Two-Factor Authentication"),
                         _("Turn off 2FA for '{user}' (for example after losing their phone)? "
                           "They can set it up again from their user menu.").format(user=r["username"]),
                         ok_text=_("Reset 2FA")):
            return

        def done(_result):
            self._reload_users()
            W.toast(self, _("2FA reset for {user}").format(user=r["username"]), "warning")
        tasks.run(self, api.reset_2fa, r["id"], on_done=done)
