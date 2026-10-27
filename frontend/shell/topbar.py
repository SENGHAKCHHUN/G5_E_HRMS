"""Top bar: breadcrumb, global search, busy indicator, clock, notifications and the user menu."""
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from core import i18n, tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from ui import theme as T
from ui import widgets as W
from ui.icons import icon

from .nav import STAFF, role_name


class TopBarMixin:
    """Part of Shell (shell/__init__.py): builds the top bar and its menus."""

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

    def _global_search(self, text: str):
        if self.role in STAFF:
            self.navigate("employees", search=text)
        else:
            self.navigate("attendance")
