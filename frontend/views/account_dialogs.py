"""Account dialogs: change password, two-factor authentication, my profile.

`force=True` is used right after login when the server says the account must first
change its temporary password or set up 2FA; closing such a dialog signs the user out.
"""
import customtkinter as ctk

from core import i18n, tasks
from core.api_client import ApiError, api
from core.i18n import _
from logic import forms, labels
from ui import theme as T
from ui import widgets as W


def _password_entry(master, label_text):
    W.label(master, label_text, size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w", padx=20, pady=(8, 4))
    e = W.entry(master, show="*", height=38)
    e.pack(fill="x", padx=20)
    return e


def _error_label(master, width=400):
    err = W.label(master, "", size=12, color=T.DANGER, wraplength=width, justify="left")
    err.pack(anchor="w", padx=20, pady=(10, 0))
    return err


def _show_error(err, error: Exception):
    if not isinstance(error, ApiError):
        raise error
    err.configure(text=str(error).split(": ", 1)[-1] if str(error).startswith(("new_password", "code")) else str(error))


def change_password(parent, force=False, on_done=None, on_cancel=None):
    title = _("Set a New Password") if force else _("Change Password")
    sub = (_("Your password is temporary. Choose your own password to continue.")
           if force else _("Use at least 8 characters with letters and numbers."))
    dlg = W.Modal(parent, title, sub, width=480, height=500, scroll=False)
    current = _password_entry(dlg.body, _("Current password (the temporary one you were given)") if force
                              else _("Current password"))
    new = _password_entry(dlg.body, _("New password"))
    confirm = _password_entry(dlg.body, _("Confirm new password"))
    err = _error_label(dlg.body)

    def cancel():
        dlg.destroy()
        if on_cancel:
            on_cancel()

    def saved(session):
        dlg.destroy()
        W.toast(parent, _("Password changed"))
        if on_done:
            on_done(session)

    def save():
        problem = forms.password_change(new.get(), confirm.get())
        if problem:
            err.configure(text=problem)
            return
        tasks.run(dlg, api.change_password, current.get(), new.get(), on_done=saved,
                  on_error=lambda e: _show_error(err, e))

    save_btn = dlg.add_button(_("Save Password"), "primary", save, "check")
    dlg.add_button(_("Sign Out") if force else _("Cancel"), "secondary", cancel)
    dlg.protocol("WM_DELETE_WINDOW", cancel)
    confirm.bind("<Return>", lambda _e: save_btn.invoke())
    current.focus_set()
    return dlg


def two_factor(parent, session, force=False, on_done=None, on_cancel=None):
    """Set up 2FA (or turn it off when it is already on)."""
    if session.get("totp_enabled") and not force:
        return _disable_two_factor(parent, session, on_done)
    tasks.run(parent, api.setup_2fa,
              on_done=lambda setup: _two_factor_setup(parent, session, setup, force, on_done, on_cancel))
    return None


def _two_factor_setup(parent, session, setup, force, on_done, on_cancel):
    sub = (_("Your role requires two-factor authentication. Set it up to continue.")
           if force else _("Protect your account with codes from an authenticator app."))
    dlg = W.Modal(parent, _("Two-Factor Authentication"), sub, width=540, height=600, scroll=False)
    b = dlg.body
    steps = _("1.  Install Google Authenticator or Microsoft Authenticator on your phone.\n"
              "2.  In the app choose  Add account  >  Enter a setup key.\n"
              "3.  Account name: {username}   ·   Type: Time based\n"
              "4.  Type the key below, then enter the 6-digit code the app shows.").format(
        username=session["username"])
    W.label(b, steps, size=12, color=T.TEXT_2, justify="left", wraplength=480).pack(anchor="w", padx=20, pady=(6, 10))
    key_box = ctk.CTkFrame(b, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
    key_box.pack(fill="x", padx=20)
    secret = setup["secret"]
    grouped = " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))
    W.label(key_box, grouped, size=15, weight="bold", mono=True, color=T.PRIMARY).pack(side="left", padx=14, pady=14)

    def copy():
        dlg.clipboard_clear()
        dlg.clipboard_append(secret)
        W.toast(dlg, _("Setup key copied"))
    W.button(key_box, _("Copy"), "secondary", "document", copy, height=30, size=12).pack(side="right", padx=10)

    W.label(b, _("6-digit code from the app"), size=12, weight="semibold", color=T.TEXT_2).pack(
        anchor="w", padx=20, pady=(16, 4))
    code = W.entry(b, "123 456", height=40)
    code.pack(fill="x", padx=20)
    err = _error_label(b, 480)

    def cancel():
        dlg.destroy()
        if on_cancel:
            on_cancel()

    def enabled(new_session):
        dlg.destroy()
        W.toast(parent, _("Two-factor authentication is on"))
        if on_done:
            on_done(new_session)

    def enable():
        if len(code.get().replace(" ", "")) != 6 or not code.get().replace(" ", "").isdigit():
            err.configure(text=_("Enter the 6-digit code from the app."))
            return
        tasks.run(dlg, api.enable_2fa, code.get(), on_done=enabled, on_error=lambda e: _show_error(err, e))

    turn_on = dlg.add_button(_("Turn On"), "primary", enable, "shield")
    dlg.add_button(_("Sign Out") if force else _("Cancel"), "secondary", cancel)
    dlg.protocol("WM_DELETE_WINDOW", cancel)
    code.bind("<Return>", lambda _e: turn_on.invoke())
    code.focus_set()


def _disable_two_factor(parent, session, on_done):
    dlg = W.Modal(parent, _("Two-Factor Authentication"), _("2FA is on for your account."), width=480,
                  height=340, scroll=False)
    if session.get("mfa_required"):
        W.label(dlg.body, _("Your role requires two-factor authentication, so it cannot be turned off. "
                            "If you lost your phone, ask an Admin to reset 2FA for your account."),
                size=13, color=T.TEXT_2, wraplength=420, justify="left").pack(anchor="w", padx=20, pady=10)
        dlg.add_button(_("Close"), "primary", dlg.destroy)
        return dlg
    pw = _password_entry(dlg.body, _("Confirm with your password to turn 2FA off"))
    err = _error_label(dlg.body)

    def disabled(new_session):
        dlg.destroy()
        W.toast(parent, _("Two-factor authentication turned off"), "warning")
        if on_done:
            on_done(new_session)

    dlg.add_button(_("Turn Off 2FA"), "danger",
                   lambda: tasks.run(dlg, api.disable_2fa, pw.get(), on_done=disabled,
                                     on_error=lambda e: _show_error(err, e)))
    dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
    pw.focus_set()
    return dlg


def my_profile(parent, session):
    """Every role can view their own employee record (README: 'own profile only')."""
    if not session.get("employee_id"):
        W.toast(parent, _("Your account is not linked to an employee record"), "warning")
        return
    tasks.run(parent, api.get_employee, session["employee_id"], on_done=lambda e: _profile(parent, session, e))


def _profile(parent, session, e):
    dlg = W.Modal(parent, _("My Profile"), f"{e['code']} • {e['position']}", width=560, height=620)
    head = W.transparent(dlg.body)
    head.pack(fill="x", padx=12, pady=(8, 12))
    W.avatar(head, e["first_name"], e["last_name"], size=64).pack(side="left")
    box = W.transparent(head)
    box.pack(side="left", padx=14)
    W.label(box, e["full_name"], size=18, weight="bold").pack(anchor="w")
    W.label(box, f"{e['department']} • {labels.show(labels.WORK_MODE, e['work_mode'])}", size=12,
            color=T.TEXT_2).pack(anchor="w")
    W.badge(box, labels.show(labels.ROLE, session["role"]), "info").pack(anchor="w", pady=(6, 0))
    grid = W.card(dlg.body, fg=T.SURFACE_ALT)
    grid.pack(fill="x", padx=12, pady=4)
    grid.grid_columnconfigure((0, 1), weight=1, uniform="p")
    fields = [(_("Username"), session["username"]), (_("Work Email"), e["email"]), (_("Phone"), e["phone"] or "-"),
              (_("Hire Date"), i18n.format_date(e["hire_date"])),
              (_("Employment"), labels.show(labels.EMPLOYMENT, e["employment"])),
              (_("Shift"), labels.show(labels.SHIFT, e["shift"])),
              (_("Base Salary"), _("{amount} / month").format(amount=W.money(e["salary"]))),
              (_("Status"), labels.show(labels.EMPLOYEE_STATUS, e["status"])),
              (_("Two-Factor Auth"), _("On") if session.get("totp_enabled") else _("Off"))]
    for i, (k, v) in enumerate(fields):
        cell = W.transparent(grid)
        cell.grid(row=i // 2, column=i % 2, sticky="w", padx=16, pady=8)
        W.micro(cell, k).pack(anchor="w")
        W.label(cell, v, size=13, weight="semibold").pack(anchor="w")
    W.label(dlg.body, _("To correct your details, contact HR."), size=12, color=T.TEXT_2).pack(
        anchor="w", padx=16, pady=(8, 0))
    dlg.add_button(_("Close"), "primary", dlg.destroy)
