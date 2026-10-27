"""Page structure: page header, KPI cards, section titles, clickable rows, grid columns."""
import tkinter as tk

import customtkinter as ctk

from .. import theme as T

from .basics import label, micro, transparent, button, tag, icon_tile


class PageHeader(ctk.CTkFrame):
    """Title card at the top of each view. Add buttons to `.actions`."""

    def __init__(self, master, title, subtitle="", eyebrow=None, chip=None, icon_name=None):
        super().__init__(master, fg_color=T.SURFACE, corner_radius=T.RADIUS_CARD,
                         border_width=1, border_color=T.BORDER)
        self.grid_columnconfigure(1, weight=1)
        if icon_name:
            icon_tile(self, icon_name, "info", size=48, icon_size=22).grid(
                row=0, column=0, padx=(20, 0), pady=20, sticky="n")
        text = transparent(self)
        text.grid(row=0, column=1, sticky="w", padx=20, pady=18)
        if eyebrow:
            micro(text, eyebrow, color=T.TEXT_2).pack(anchor="w")
        title_row = transparent(text)
        title_row.pack(anchor="w")
        label(title_row, title, size=22, weight="bold").pack(side="left")
        self.chip = None
        if chip is not None:
            self.chip = tag(title_row, chip, "info")
            self.chip.pack(side="left", padx=(12, 0))
        self.subtitle = label(text, subtitle, size=13, color=T.TEXT_2)
        self.subtitle.pack(anchor="w", pady=(2, 0))
        self.actions = transparent(self)
        self.actions.grid(row=0, column=2, sticky="e", padx=20)

    def add_action(self, text, kind="secondary", icon_name=None, command=None):
        b = button(self.actions, text, kind=kind, icon_name=icon_name, command=command, height=38)
        b.pack(side="left", padx=(8, 0))
        return b


class KpiCard(ctk.CTkFrame):
    def __init__(self, master, title, value, unit="", icon_name=None, icon_kind="info",
                 value_color=T.TEXT, unit_color=T.TEXT_2):
        super().__init__(master, fg_color=T.SURFACE, corner_radius=T.RADIUS_CARD,
                         border_width=1, border_color=T.BORDER)
        top = transparent(self)
        top.pack(fill="x", padx=18, pady=(16, 0))
        micro(top, title).pack(side="left")
        if icon_name:
            icon_tile(top, icon_name, icon_kind, size=32, icon_size=16).pack(side="right")
        row = transparent(self)
        row.pack(fill="x", padx=18, pady=(4, 0))
        self.value_label = label(row, value, size=30, weight="bold", color=value_color)
        self.value_label.pack(side="left")
        if unit:
            label(row, unit, size=13, color=unit_color).pack(side="left", padx=(8, 0), pady=(10, 0))
        self.footer = transparent(self)
        self.footer.pack(fill="x", padx=18, pady=(6, 16))


def section_title(master, title, subtitle=None, chip=None, dot=None):
    box = transparent(master)
    row = transparent(box)
    row.pack(anchor="w", fill="x")
    if dot:
        ctk.CTkLabel(row, text="●", text_color=dot, font=T.font(12)).pack(side="left", padx=(0, 8))
    label(row, title, size=16, weight="semibold").pack(side="left")
    if chip:
        tag(row, chip, "info").pack(side="left", padx=(10, 0))
    if subtitle:
        label(box, subtitle, size=12, color=T.TEXT_2).pack(anchor="w", pady=(2, 0))
    return box


def make_clickable(widget, command, hover_frame=None, hover=T.ROW_HOVER, base=None):
    """Bind a click on a frame and all its children; optional hover tint."""
    def bind(w):
        w.bind("<Button-1>", lambda _e: command(), add="+")
        try:
            w.configure(cursor="hand2")
        except (tk.TclError, ValueError):
            pass
        for child in w.winfo_children():
            bind(child)
    bind(widget)
    if hover_frame is not None:
        base = base if base is not None else hover_frame.cget("fg_color")
        hover_frame.bind("<Enter>", lambda _e: hover_frame.configure(fg_color=hover), add="+")
        hover_frame.bind("<Leave>", lambda e: (
            None if _contains(hover_frame, e) else hover_frame.configure(fg_color=base)), add="+")


def _contains(frame, event):
    w = frame.winfo_containing(event.x_root, event.y_root)
    while w is not None:
        if w == frame:
            return True
        w = w.master
    return False


def grid_columns(frame, n, weight=1, uniform="kpi"):
    for i in range(n):
        frame.grid_columnconfigure(i, weight=weight, uniform=uniform)
