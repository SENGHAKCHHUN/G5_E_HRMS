"""Main application window: login screen <-> sidebar shell with swappable views."""
import tkinter as tk

import customtkinter as ctk

from core import tasks
from core.api_client import ApiError, SessionExpired, api
from core.i18n import _
from core.state import state
from ui import theme as T
from shell import Shell
from ui import widgets as W
from views.login_view import LoginView


LOGIN_SIZE = (480, 700)
MAIN_SIZE = (1280, 800)
MIN_SIZE = (1024, 680)
REBUILD_WAIT_MS = 3000  # longest a rebuilt screen waits for its data before it is shown anyway


class HRMSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(_("HRMS"))
        self.configure(fg_color=T.BG)
        W._set_window_icon(self)
        self.current = None
        self._next = None  # screen being built in the background by rebuild()
        tasks.set_error_handler(self.handle_error)
        self.show_login()

    # -------------------------------------------------------------- errors
    def handle_error(self, error: Exception):
        """App-wide handler for failed background calls and button callbacks."""
        if isinstance(error, SessionExpired):
            self.session_expired(str(error))
        elif isinstance(error, ApiError):
            W.toast(self, str(error), "danger", ms=5000)
        else:
            raise error

    def report_callback_exception(self, exc_type, exc, tb):
        if isinstance(exc, ApiError):
            self.handle_error(exc)
            return
        if isinstance(exc, tk.TclError) and "bad window path name" in str(exc):
            return  # CTk re-focusing a widget that was closed a moment earlier - harmless
        super().report_callback_exception(exc_type, exc, tb)

    def session_expired(self, message: str):
        if isinstance(self.current, LoginView):
            return
        self.show_login(message=message)

    # ------------------------------------------------------------- windows
    def _screen(self):
        """Screen size in CTk (unscaled) units."""
        scale = self._get_window_scaling()
        return int(self.winfo_screenwidth() / scale), int(self.winfo_screenheight() / scale)

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self._screen()
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 30)}")

    def _swap(self, frame):
        if self._next is not None and self._next is not frame:  # e.g. logged out while a rebuild was waiting
            self._next.destroy()
            self._next = None
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_login(self, message: str = ""):
        api.logout()
        state.sign_out()
        self.title(_("HRMS"))
        sw, sh = self._screen()
        size = (LOGIN_SIZE[0], min(LOGIN_SIZE[1], sh - 90))
        self.minsize(*size)
        self._center(*size)
        self.resizable(False, False)
        self._swap(LoginView(self, on_success=self.after_login, message=message))

    def after_login(self, session: dict):
        """Finish any step the server requires (new password, 2FA setup), then load settings."""
        from views import account_dialogs
        action = session.get("pending_action")
        if action == "password_change_required":
            account_dialogs.change_password(self.current, force=True, on_done=self.after_login,
                                            on_cancel=self.show_login)
        elif action == "mfa_setup_required":
            account_dialogs.two_factor(self.current, session, force=True, on_done=self.after_login,
                                       on_cancel=self.show_login)
        else:
            state.session = session
            tasks.run(self, api.get_settings, on_done=lambda s: self._enter(s))

    def _enter(self, settings: dict):
        state.settings = settings
        self.show_main()

    def show_main(self, view: str = "dashboard"):
        self.resizable(True, True)
        sw, sh = self._screen()
        w, h = min(MAIN_SIZE[0], sw - 40), min(MAIN_SIZE[1], sh - 90)  # leave room for the taskbar
        self.minsize(min(MIN_SIZE[0], w), min(MIN_SIZE[1], h))
        self._center(w, h)
        self._swap(Shell(self, view))

    def rebuild(self, view: str):
        """Rebuild the whole window (after changing language, accent colour or scaling).

        The new screen is built behind the current one and swapped in once its data has
        loaded, so the user never sees a blank or "Loading..." screen in between.
        """
        self.title(_("HRMS"))
        if self._next is not None:  # switched again before the previous rebuild finished
            self._next.destroy()
        if isinstance(self.current, LoginView):
            frame = LoginView(self, on_success=self.after_login)
        else:
            frame = Shell(self, view)
        frame.place(x=0, y=0, relwidth=1, relheight=1)
        frame.lower(self.current)
        self._next = frame
        self._swap_when_ready(frame, waited=0)

    def _swap_when_ready(self, frame, waited: int):
        if frame is not self._next:
            return
        if tasks.pending() and waited < REBUILD_WAIT_MS:
            self.after(30, self._swap_when_ready, frame, waited + 30)
            return
        self._next = None
        frame.place_forget()
        self._swap(frame)
