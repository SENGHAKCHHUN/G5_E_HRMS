"""Screen 1 - Login."""
import customtkinter as ctk

from core import i18n, prefs, tasks
from core.api_client import ApiError, api
from core.i18n import _
from core.state import state
from ui import theme as T
from ui import widgets as W
from ui.icons import logo


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_success, message: str = ""):
        super().__init__(master, fg_color=T.BG, corner_radius=0)
        self.app = master
        self.on_success = on_success

        lang = W.segmented(self, list(i18n.LANGUAGES.values()), command=self._pick_language, height=28)
        lang.set(i18n.LANGUAGES[state.language])
        lang.place(relx=1.0, x=-16, y=14, anchor="ne")

        box = W.transparent(self)
        box.place(relx=0.5, rely=0.52, anchor="center", relwidth=0.84)

        ctk.CTkLabel(box, text="", image=logo(56)).pack(pady=(0, 10))
        W.label(box, _("HR Management System"), size=22, weight="bold", anchor="center").pack()
        W.label(box, _("Sign in to access your enterprise portal"), size=12, color=T.TEXT_2,
                anchor="center").pack(pady=(2, 16))

        W.label(box, _("Username / Work Email"), size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w")
        self.user = W.entry(box, _("Username or work email"), height=40)
        self.user.pack(fill="x", pady=(4, 12))

        W.label(box, _("Password"), size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w")
        pw_row = W.transparent(box)
        pw_row.pack(fill="x", pady=(4, 10))
        self.pw = W.entry(pw_row, _("Password"), height=40, show="*")
        self.pw.pack(side="left", fill="x", expand=True)
        W.icon_button(pw_row, "view", self._toggle_pw, kind="secondary", size=40, fallback="👁").pack(
            side="left", padx=(8, 0))

        # shown only when the account has two-factor authentication
        self.otp_box = W.transparent(box)
        W.label(self.otp_box, _("Authentication code (from your authenticator app)"), size=12,
                weight="semibold", color=T.TEXT_2).pack(anchor="w")
        self.otp = W.entry(self.otp_box, _("6-digit code"), height=40)
        self.otp.pack(fill="x", pady=(4, 10))
        self.otp.bind("<Return>", lambda _e: self.submit())

        self.options_row = W.transparent(box)
        self.options_row.pack(fill="x", pady=(0, 14))
        self.remember = ctk.CTkCheckBox(self.options_row, text=_("Remember me"), font=T.font(12),
                                        text_color=T.TEXT_2, checkbox_width=18, checkbox_height=18,
                                        corner_radius=4, fg_color=T.PRIMARY, border_color=T.BORDER, border_width=2)
        self.remember.pack(side="left")
        W.button(self.options_row, _("Forgot Password?"), "link", height=26, size=12,
                 command=self._forgot).pack(side="right")

        self.signin = W.button(box, _("SIGN IN"), "primary", command=self.submit, height=42, size=14)
        self.signin.pack(fill="x")
        self.error = W.label(box, message, size=12, color=T.WARNING if message else T.DANGER, anchor="center",
                             wraplength=360)
        self.error.pack(fill="x", pady=(6, 0))

        status = W.transparent(box)
        status.pack(pady=(4, 0))
        self.status_dot = ctk.CTkLabel(status, text="●", text_color=T.TEXT_3, font=T.font(11))
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_text = W.label(status, _("Checking the server..."), size=11, color=T.TEXT_2)
        self.status_text.pack(side="left")
        tasks.run(self, api.health, on_done=self._show_health)

        saved = prefs.load()
        if saved["remember"] and saved["username"]:
            self.user.insert(0, saved["username"])
            self.remember.select()
            self.after(100, self.pw.focus_set)
        else:
            self.after(100, self.user.focus_set)
        self.user.bind("<Return>", lambda _e: self.submit())
        self.pw.bind("<Return>", lambda _e: self.submit())

    def _show_health(self, result):
        online, msg = result
        self.status_dot.configure(text_color=T.SUCCESS if online else T.WARNING)
        self.status_text.configure(text=_("API Status: {message}").format(message=msg))

    def _pick_language(self, name: str):
        code = next(c for c, n in i18n.LANGUAGES.items() if n == name)
        if code != state.language:
            state.set_language(code)
            self.app.rebuild("dashboard")

    def _toggle_pw(self):
        self.pw.configure(show="" if self.pw.cget("show") == "*" else "*")

    def _forgot(self):
        W.info_dialog(self, _("Forgot Password"),
                      _("Ask an Admin to reset your password (Settings > Authentication & Users > User Accounts > "
                        "Reset Password).\n\nYou will get a one-time temporary password and choose your own "
                        "password the next time you sign in."), height=320)

    def _show_otp(self):
        if not self.otp_box.winfo_ismapped():
            self.otp_box.pack(fill="x", before=self.options_row)
        self.otp.focus_set()

    def submit(self):
        username, password = self.user.get().strip(), self.pw.get()
        if not username or not password:
            self.error.configure(text=_("Please enter your username and password."), text_color=T.DANGER)
            return
        otp = self.otp.get().strip() if self.otp_box.winfo_ismapped() else None
        self.signin.configure(state="disabled", text=_("Signing in..."))
        tasks.run(self, api.login, username, password, otp=otp or None,
                  on_done=lambda session: self._signed_in(session, username), on_error=self._failed)

    def _failed(self, error: Exception):
        self.signin.configure(state="normal", text=_("SIGN IN"))
        if not isinstance(error, ApiError):
            raise error
        if str(error) == "otp_required":
            self._show_otp()
            self.error.configure(text=_("Enter the code from your authenticator app."), text_color=T.TEXT_2)
        else:
            self.error.configure(text=str(error), text_color=T.DANGER)

    def _signed_in(self, session: dict, username: str):
        prefs.save(remember=bool(self.remember.get()), username=username if self.remember.get() else "")
        self.on_success(session)
