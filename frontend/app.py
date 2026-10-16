"""Main application window: login screen <-> sidebar shell with swappable views."""
import importlib
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from core import i18n, prefs, tasks
from core.api_client import ApiError, SessionExpired, api
from core.i18n import N_, _
from core.state import state
from ui import theme as T
from ui import widgets as W
from ui.icons import icon, logo
from views.login_view import LoginView

ALL = {"Admin", "HR Manager", "Employee"}
STAFF = {"Admin", "HR Manager"}

# key, sidebar label (translated when shown), icon, roles, module, class
NAV = [
    ("dashboard", N_("Dashboard"), "dashboard", ALL, "views.dashboard_view", "DashboardView"),
    ("employees", N_("Employee Directory"), "people", STAFF, "views.employee_view", "EmployeeView"),
    ("departments", N_("Departments & Positions"), "org", STAFF, "views.department_view", "DepartmentView"),
    ("attendance", N_("Attendance & Time"), "clock", ALL, "views.attendance_view", "AttendanceView"),
    ("leave", N_("Leave Management"), "calendar", ALL, "views.leave_view", "LeaveView"),
    ("payroll", N_("Payroll & Payslips"), "payroll", ALL, "views.payroll_view", "PayrollView"),
    ("settings", N_("Settings"), "settings", {"Admin"}, "views.settings_view", "SettingsView"),
]
ROLE_NAMES = {"Admin": N_("Admin"), "HR Manager": N_("HR Manager"), "Employee": N_("Employee")}

LOGIN_SIZE = (480, 700)
MAIN_SIZE = (1280, 800)
MIN_SIZE = (1024, 680)


def role_name(role: str) -> str:
    return _(ROLE_NAMES.get(role, role))


class HRMSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(_("HRMS"))
        self.configure(fg_color=T.BG)
        W._set_window_icon(self)
        self.current = None
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
        """Rebuild the whole window (after changing language, accent colour or scaling)."""
        self.title(_("HRMS"))
        if isinstance(self.current, LoginView):
            self.show_login()
        else:
            self._swap(Shell(self, view))


class Shell(ctk.CTkFrame):
    """Sidebar + top bar + content area. Views are created lazily and cached."""

    def __init__(self, app: HRMSApp, start_view: str = "dashboard"):
        super().__init__(app, fg_color=T.BG, corner_radius=0)
        self.app = app
        self.session = state.session
        self.role = self.session["role"]
        self.nav = [n for n in NAV if self.role in n[3]]
        self.pages: dict[str, tuple] = {}          # key -> (scroll frame, view)
        self.active: str | None = None
        self._clock_job = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        content = W.transparent(self)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        self._build_topbar(content)
        self.page_host = W.transparent(content)
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        tasks.set_busy_listener(self._set_busy)
        self.navigate(start_view if any(n[0] == start_view for n in self.nav) else "dashboard")
        self._tick()
        self.load_notifications()

    # --------------------------------------------------------------- sidebar
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=T.SIDEBAR_WIDTH, fg_color=T.SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        sb.pack_propagate(False)
        # thin line between sidebar and content (visible in light mode); packed first to span full height
        ctk.CTkFrame(sb, width=1, fg_color=T.SIDEBAR_BORDER, corner_radius=0).pack(side="right", fill="y")

        brand = W.transparent(sb)
        brand.pack(fill="x", padx=16, pady=(18, 22))
        ctk.CTkLabel(brand, text="", image=logo(38)).pack(side="left")
        txt = W.transparent(brand)
        txt.pack(side="left", padx=10)
        W.label(txt, "HRMS", size=16, weight="bold", color=T.SIDEBAR_TITLE).pack(anchor="w")
        W.label(txt, _("HR Management System"), size=11, color=T.SIDEBAR_MUTED).pack(anchor="w")

        self.nav_buttons = {}
        for key, text, icon_name, *_rest in self.nav:
            b = ctk.CTkButton(
                sb, text=_(text), anchor="w", height=40, corner_radius=T.RADIUS_BTN,
                font=T.font(13, "semibold"), fg_color="transparent", hover_color=T.SIDEBAR_HOVER,
                text_color=T.SIDEBAR_TEXT, image=icon(icon_name, 16, T.SIDEBAR_MUTED),
                compound="left", border_spacing=10, command=lambda k=key: self.navigate(k))
            b.pack(fill="x", padx=12, pady=2)
            b._icon_name = icon_name
            self.nav_buttons[key] = b

        bottom = W.transparent(sb)
        bottom.pack(side="bottom", fill="x", padx=12, pady=16)
        lang = ctk.CTkFrame(bottom, fg_color="transparent")
        lang.pack(fill="x", pady=(0, 8))
        self.lang_switch = W.segmented(lang, list(i18n.LANGUAGES.values()), command=self._pick_language)
        self.lang_switch.set(i18n.LANGUAGES[state.language])
        self.lang_switch.pack(fill="x")
        mode = ctk.CTkFrame(bottom, fg_color=T.SIDEBAR_HOVER, corner_radius=T.RADIUS_BTN, height=40)
        mode.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(mode, text="", image=icon("moon", 15, T.SIDEBAR_TEXT)).pack(side="left", padx=(12, 8))
        W.label(mode, _("Dark Mode"), size=13, color=T.SIDEBAR_TEXT).pack(side="left", pady=8)
        self.dark_var = tk.BooleanVar(value=ctk.get_appearance_mode() == "Dark")
        W.switch(mode, command=self.toggle_theme, variable=self.dark_var).pack(side="right", padx=8)

        ctk.CTkButton(bottom, text=_("Logout"), anchor="w", height=40, corner_radius=T.RADIUS_BTN,
                      font=T.font(13, "semibold"), fg_color="transparent",
                      hover_color=T.SIDEBAR_HOVER, text_color=T.SIDEBAR_DANGER,
                      image=icon("logout", 16, T.SIDEBAR_DANGER), compound="left",
                      border_spacing=10, command=self.logout).pack(fill="x")

    def _highlight(self, key):
        for k, b in self.nav_buttons.items():
            active = k == key
            b.configure(fg_color=T.PRIMARY if active else "transparent",
                        hover_color=T.PRIMARY_HOVER if active else T.SIDEBAR_HOVER,
                        text_color=T.WHITE if active else T.SIDEBAR_TEXT,
                        image=icon(b._icon_name, 16, T.WHITE if active else T.SIDEBAR_MUTED))

    # ---------------------------------------------------------------- topbar
    def _build_topbar(self, master):
        bar = W.transparent(master, height=68)
        bar.grid(row=0, column=0, sticky="ew", padx=20)
        bar.grid_columnconfigure(1, weight=1)

        crumbs = W.transparent(bar)
        crumbs.grid(row=0, column=0, sticky="w", pady=14)
        W.label(crumbs, _("System"), size=13, color=T.TEXT_2).pack(side="left")
        W.label(crumbs, "  ›  ", size=13, color=T.TEXT_3).pack(side="left")
        self.crumb = W.label(crumbs, "", size=13, weight="semibold", color=T.PRIMARY)
        self.crumb.pack(side="left")

        placeholder = _("Search employee, department...") if self.role in STAFF else _("Search...")
        self.search = W.SearchEntry(bar, placeholder, on_submit=self._global_search, width=320)
        self.search.grid(row=0, column=1, sticky="w", padx=20)

        right = W.transparent(bar)
        right.grid(row=0, column=2, sticky="e")
        self.busy = W.label(right, "", size=12, color=T.TEXT_3)
        self.busy.pack(side="left", padx=(0, 10))
        chip = ctk.CTkFrame(right, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN, border_width=1,
                            border_color=T.BORDER)
        chip.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(chip, text="", image=icon("calendar", 14, T.TEXT_2)).pack(side="left", padx=(12, 6))
        self.clock_label = W.label(chip, "", size=12, weight="semibold")
        self.clock_label.pack(side="left", padx=(0, 12), pady=7)

        self.bell_box = W.transparent(right)
        self.bell_box.pack(side="left", padx=(0, 14))
        W.icon_button(self.bell_box, "bell", self._show_notifications, kind="secondary", size=38,
                      fallback="🔔").pack()
        self.notifications: list[str] = []
        self.badge = None
        user = W.transparent(right)
        user.pack(side="left")
        names = W.transparent(user)
        names.pack(side="left", padx=(0, 10))
        W.label(names, self.session["name"], size=13, weight="semibold", anchor="e").pack(anchor="e")
        W.label(names, role_name(self.role), size=11, color=T.TEXT_2, anchor="e").pack(anchor="e")
        av = W.avatar(user, text=self.session["initials"], size=38, color=T.PRIMARY)
        av.pack(side="left")
        av.bind("<Button-1>", self._user_menu)
        av.configure(cursor="hand2")

    def _set_busy(self, busy: bool):
        try:
            self.busy.configure(text=("⟳ " + _("Loading...")) if busy else "")
        except tk.TclError:
            pass

    def _tick(self):
        now = datetime.now()
        self.clock_label.configure(text=f"{i18n.format_date(now.date())} • {i18n.format_time(now, seconds=True)}")
        self._clock_job = self.after(1000, self._tick)

    def load_notifications(self):
        tasks.run(self, api.get_notifications, on_done=self._show_badge, on_error=lambda _e: None)

    def _show_badge(self, notes: list[str]):
        self.notifications = notes
        count = 0 if len(notes) == 1 and notes[0] == _("You're all caught up") else len(notes)
        if self.badge is not None:
            self.badge.destroy()
            self.badge = None
        if count:
            self.badge = ctk.CTkLabel(self.bell_box, text=str(count), width=16, height=16, corner_radius=8,
                                      fg_color=T.DANGER, text_color=T.WHITE, font=T.font(9, "bold"))
            self.badge.place(relx=1.0, rely=0.0, x=-6, y=-2, anchor="ne")

    def _menu(self):
        return tk.Menu(self, tearoff=0, bg=T.pick(T.SURFACE), fg=T.pick(T.TEXT), activebackground=T.pick(T.PRIMARY),
                       activeforeground="#FFFFFF", bd=0, font=T.menu_font())

    def _show_notifications(self):
        m = self._menu()
        for note in self.notifications or [_("You're all caught up")]:
            m.add_command(label="●  " + note,
                          command=lambda: self.navigate("leave" if self.role != "Employee" else "dashboard"))
        x, y = self.winfo_pointerxy()
        m.tk_popup(x - 260, y + 16)

    def _user_menu(self, _event=None):
        from views import account_dialogs
        m = self._menu()
        m.add_command(label=f"{self.session['name']}  ({self.session['username']})", state="disabled")
        m.add_separator()
        m.add_command(label=_("My Profile"), command=lambda: account_dialogs.my_profile(self, self.session))
        m.add_command(label=_("Change Password"),
                      command=lambda: account_dialogs.change_password(self, on_done=self._session_updated))
        status = _("On") if self.session.get("totp_enabled") else _("Off")
        m.add_command(label=_("Two-Factor Authentication: {status}").format(status=status),
                      command=lambda: account_dialogs.two_factor(self, self.session, on_done=self._session_updated))
        languages = tk.Menu(m, tearoff=0, bg=T.pick(T.SURFACE), fg=T.pick(T.TEXT), font=(T.khmer_family(), 10))
        for code, name in i18n.LANGUAGES.items():
            languages.add_radiobutton(label=name, value=code, variable=tk.StringVar(value=state.language),
                                      command=lambda c=code: self.change_language(c))
        m.add_cascade(label=_("Language"), menu=languages)
        m.add_separator()
        if self.role == "Admin":
            m.add_command(label=_("Settings"), command=lambda: self.navigate("settings"))
        m.add_command(label=_("Toggle dark mode"),
                      command=lambda: (self.dark_var.set(not self.dark_var.get()), self.toggle_theme()))
        m.add_command(label=_("Logout"), command=self.logout)
        x, y = self.winfo_pointerxy()
        m.tk_popup(x - 200, y + 16)

    def _session_updated(self, session: dict):
        self.session.update(session)

    def _pick_language(self, name: str):
        code = next(c for c, n in i18n.LANGUAGES.items() if n == name)
        self.change_language(code)

    def change_language(self, code: str):
        if code == state.language:
            return
        state.set_language(code)
        self.app.rebuild(self.active or "dashboard")

    def _global_search(self, text: str):
        if self.role in STAFF:
            self.navigate("employees", search=text)
        else:
            self.navigate("attendance")

    # ------------------------------------------------------------ navigation
    def navigate(self, key: str, **kwargs):
        entry = next((n for n in self.nav if n[0] == key), None)
        if entry is None:  # not permitted for this role
            W.toast(self, _("You do not have access to that module"), "warning")
            return
        if self.active and self.active in self.pages:
            self.pages[self.active][0].grid_forget()
        if key not in self.pages:
            scroll = ctk.CTkScrollableFrame(self.page_host, fg_color=T.BG, corner_radius=0,
                                            scrollbar_button_color=T.ELEVATED,
                                            scrollbar_button_hover_color=T.ELEVATED_HOVER)
            cls = getattr(importlib.import_module(entry[4]), entry[5])
            view = cls(scroll, self)
            view.pack(fill="both", expand=True, padx=(20, 12), pady=(0, 20))
            self.pages[key] = (scroll, view)
        scroll, view = self.pages[key]
        scroll.grid(row=0, column=0, sticky="nsew")
        self.active = key
        self._highlight(key)
        self.crumb.configure(text=_(entry[1]))
        if hasattr(view, "on_show"):
            view.on_show(**kwargs)

    def refresh_view(self, key: str | None = None, **kwargs):
        """Destroy and rebuild a view (used after data changes / theme switch)."""
        key = key or self.active
        if key in self.pages:
            self.pages.pop(key)[0].destroy()
        if key == self.active:
            self.active = None
            self.navigate(key, **kwargs)

    def invalidate(self, *keys: str):
        """Drop cached views so they rebuild with fresh data next time they open."""
        for k in keys:
            if k != self.active and k in self.pages:
                self.pages.pop(k)[0].destroy()
        self.load_notifications()

    def toggle_theme(self):
        self.set_theme("dark" if self.dark_var.get() else "light")

    def set_theme(self, mode: str):
        """mode: dark | light | system"""
        self.app.focus_set()  # CTk re-focuses the focused widget after a mode switch; it must survive
        ctk.set_appearance_mode(mode)
        state.theme = mode
        prefs.save(theme=mode)
        self.dark_var.set(ctk.get_appearance_mode() == "Dark")
        for k in list(self.pages):  # matplotlib charts and tk menus are not CTk-aware: rebuild views
            if k != self.active:
                self.pages.pop(k)[0].destroy()
        self.refresh_view()

    def logout(self):
        self.app.show_login()

    def destroy(self):
        if self._clock_job:
            self.after_cancel(self._clock_job)
            self._clock_job = None
        super().destroy()
