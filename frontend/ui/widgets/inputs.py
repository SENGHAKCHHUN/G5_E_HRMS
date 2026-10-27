"""Form controls: text entry, search box, option menu, segmented button, progress bar, switch."""
import customtkinter as ctk

from core.i18n import _

from .. import theme as T
from ..icons import icon


def entry(master, placeholder="", width=200, height=36, textvariable=None, **kw):
    return ctk.CTkEntry(master, placeholder_text=placeholder, width=width, height=height,
                        corner_radius=T.RADIUS_INPUT, border_width=1, border_color=T.BORDER,
                        fg_color=T.INPUT, text_color=T.TEXT, placeholder_text_color=T.TEXT_3,
                        font=T.font(13), textvariable=textvariable, **kw)


class SearchEntry(ctk.CTkFrame):
    """Entry with a leading search icon. `on_change(text)` fires on every key."""

    def __init__(self, master, placeholder=None, on_change=None, on_submit=None,
                 width=260, height=38):
        super().__init__(master, fg_color=T.INPUT, corner_radius=T.RADIUS_INPUT,
                         border_width=1, border_color=T.BORDER, height=height, width=width)
        img = icon("search", 15, T.TEXT_3)
        ctk.CTkLabel(self, text="" if img else "⌕", image=img, width=20,
                     text_color=T.TEXT_3).pack(side="left", padx=(12, 4))
        # no textvariable: CTkEntry drops its placeholder when one is attached
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder or _("Search..."), width=width - 50,
                                  border_width=0, fg_color=T.INPUT, text_color=T.TEXT,
                                  placeholder_text_color=T.TEXT_3, font=T.font(13), height=height - 4)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._last = ""
        if on_change:
            def changed(_e):
                if self.get() != self._last:
                    self._last = self.get()
                    on_change(self._last)
            self.entry.bind("<KeyRelease>", changed)
        if on_submit:
            self.entry.bind("<Return>", lambda _e: on_submit(self.get()))

    def get(self):
        return self.entry.get()

    def set(self, text):
        self.entry.delete(0, "end")
        if text:
            self.entry.insert(0, text)
        self._last = text


def option_menu(master, values, command=None, width=180, variable=None, height=36):
    return ctk.CTkOptionMenu(
        master, values=values, command=command, width=width, height=height, variable=variable,
        corner_radius=T.RADIUS_INPUT, fg_color=T.ELEVATED, button_color=T.ELEVATED,
        button_hover_color=T.ELEVATED_HOVER, text_color=T.TEXT, font=T.font(13, "semibold"),
        dropdown_fg_color=T.SURFACE, dropdown_hover_color=T.ELEVATED,
        dropdown_text_color=T.TEXT, dropdown_font=T.font(13), dynamic_resizing=False)


def segmented(master, values, command=None, variable=None, height=32):
    return ctk.CTkSegmentedButton(
        master, values=values, command=command, variable=variable, height=height,
        corner_radius=T.RADIUS_BTN, fg_color=T.INPUT, selected_color=T.SEG_SELECTED,
        selected_hover_color=T.SEG_SELECTED_HOVER, unselected_color=T.INPUT,
        unselected_hover_color=T.ELEVATED, text_color=(T.TEXT[0], T.TEXT[1]),
        font=T.font(12, "semibold"))


def progress(master, value, color=T.PRIMARY, height=8, width=None):
    kw = {"width": width} if width else {}
    bar = ctk.CTkProgressBar(master, height=height, corner_radius=height // 2,
                             fg_color=T.INPUT, progress_color=color, **kw)
    bar.set(max(0.0, min(1.0, value)))
    return bar


def switch(master, command=None, on=False, variable=None):
    sw = ctk.CTkSwitch(master, text="", command=command, variable=variable, width=46,
                       switch_width=40, switch_height=20, progress_color=T.PRIMARY,
                       button_color="#FFFFFF", button_hover_color="#E2E8F0",
                       fg_color=T.ELEVATED_HOVER)
    if on and variable is None:
        sw.select()
    return sw
