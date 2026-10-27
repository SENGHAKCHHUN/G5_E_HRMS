"""The signed-in window: sidebar + top bar + content area with the screens.

Shell is built from three parts:
    sidebar.py   SidebarMixin  - brand, screen buttons, language, dark mode, logout
    topbar.py    TopBarMixin   - breadcrumb, search, clock, notifications, user menu
    this file    Shell         - layout, navigation between screens, theme and language
The screens themselves (sidebar entries and who may open them) are listed in nav.py.
"""
import importlib

import customtkinter as ctk

from core import i18n, prefs, tasks
from core.i18n import _
from core.state import state
from ui import theme as T
from ui import widgets as W

from .nav import NAV
from .sidebar import SidebarMixin
from .topbar import TopBarMixin


class Shell(SidebarMixin, TopBarMixin, ctk.CTkFrame):
    """Sidebar + top bar + content area. Views are created lazily and cached."""

    def __init__(self, app, start_view: str = "dashboard"):  # app: the HRMSApp window
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

    # -------------------------------------------------------------- language
    def _pick_language(self, name: str):
        code = next(c for c, n in i18n.LANGUAGES.items() if n == name)
        self.change_language(code)

    def change_language(self, code: str):
        if code == state.language:
            return
        state.set_language(code)
        self.app.rebuild(self.active or "dashboard")

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
        """Destroy and rebuild a view (used after data changes)."""
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
        # CTk widgets and charts recolour themselves in place, and menus are built when opened,
        # so nothing is rebuilt and the open screen keeps its data
        ctk.set_appearance_mode(mode)
        state.theme = mode
        prefs.save(theme=mode)
        self.dark_var.set(ctk.get_appearance_mode() == "Dark")

    def logout(self):
        self.app.show_login()

    def destroy(self):
        if self._clock_job:
            self.after_cancel(self._clock_job)
            self._clock_job = None
        super().destroy()
