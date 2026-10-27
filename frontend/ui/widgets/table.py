"""Data table with header, rows and footer, its cell helpers, and the paginator."""
import math

import customtkinter as ctk

from core.i18n import _

from .. import theme as T

from .basics import label, micro, transparent, button, avatar
from .layout import _contains


class DataTable(ctk.CTkFrame):
    """Lightweight data grid built from CTk frames so cells can hold badges/buttons.

    columns: list of dicts {key, title, weight=1, anchor='w', render=None}
    render(parent, row) -> widget  (custom cell)
    """

    def __init__(self, master, columns, empty_text=None, row_height=54, header=True):
        super().__init__(master, fg_color=T.SURFACE, corner_radius=T.RADIUS_CARD,
                         border_width=1, border_color=T.BORDER)
        self.columns = columns
        self.row_height = row_height
        self.empty_text = empty_text or _("No records found")
        if header:
            head = ctk.CTkFrame(self, fg_color=T.INPUT, corner_radius=0, height=44)
            head.pack(fill="x", padx=1, pady=(T.RADIUS_CARD, 0))
            self._configure_cols(head)
            head.grid_rowconfigure(0, minsize=44)
            for i, c in enumerate(columns):
                micro(head, c["title"], anchor="e" if c.get("anchor") == "e" else "w",
                      justify="right" if c.get("anchor") == "e" else "left").grid(
                    row=0, column=i, sticky="ew", padx=12)
        self.body = transparent(self)
        self.body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.footer = transparent(self)
        self.footer.pack(fill="x", padx=16, pady=(0, 10))

    def _configure_cols(self, frame):
        for i, c in enumerate(self.columns):
            frame.grid_columnconfigure(i, weight=c.get("weight", 1), uniform="cols")

    def set_loading(self):
        """Show a 'Loading...' placeholder while the rows are fetched in the background."""
        for w in self.body.winfo_children():
            w.destroy()
        label(self.body, _("Loading..."), color=T.TEXT_3, anchor="center").pack(fill="x", pady=40)

    def set_rows(self, rows):
        for w in self.body.winfo_children():
            w.destroy()
        if not rows:
            label(self.body, self.empty_text, color=T.TEXT_2, anchor="center").pack(fill="x", pady=40)
            return
        for idx, row in enumerate(rows):
            bg = T.SURFACE if idx % 2 == 0 else T.SURFACE_ALT
            r = ctk.CTkFrame(self.body, fg_color=bg, corner_radius=0)
            r.pack(fill="x")
            self._configure_cols(r)
            r.grid_rowconfigure(0, minsize=self.row_height)
            for i, c in enumerate(self.columns):
                if c.get("render"):
                    cell = c["render"](r, row)
                else:
                    val = row.get(c["key"], "")
                    cell = label(r, "" if val is None else str(val), size=13,
                                 anchor="e" if c.get("anchor") == "e" else "w", wraplength=180)
                if cell is not None:
                    sticky = {"e": "e", "center": ""}.get(c.get("anchor"), "w")
                    cell.grid(row=0, column=i, sticky=sticky, padx=12, pady=6)
            self._bind_hover(r, bg)

    @staticmethod
    def _bind_hover(row, bg):
        def on_enter(_e):
            row.configure(fg_color=T.ROW_HOVER)

        def on_leave(e):
            if not _contains(row, e):
                row.configure(fg_color=bg)

        row.bind("<Enter>", on_enter, add="+")
        row.bind("<Leave>", on_leave, add="+")


def cell_stack(master, title, subtitle, title_mono=False):
    """Two-line cell: bold title + muted subtitle."""
    box = transparent(master)
    label(box, title, size=13, weight="semibold", mono=title_mono).pack(anchor="w")
    if subtitle:
        label(box, subtitle, size=11, color=T.TEXT_2).pack(anchor="w")
    return box


def person_cell(master, first, last, subtitle=""):
    box = transparent(master)
    avatar(box, first, last, size=34).pack(side="left", padx=(0, 10))
    cell_stack(box, f"{first} {last}", subtitle).pack(side="left")
    return box


def dot_text(master, text, color=T.TEXT_2):
    box = transparent(master)
    ctk.CTkLabel(box, text="●", font=T.font(9), text_color=color, width=10).pack(side="left", padx=(0, 6))
    label(box, text, size=13, wraplength=150).pack(side="left")
    return box


class Paginator(ctk.CTkFrame):
    """Previous / Next paging. Server-side: read `limit`/`offset`, then call update(total, shown).
    Client-side lists: call slice(rows)."""

    def __init__(self, master, on_change, page_size=8):
        super().__init__(master, fg_color="transparent")
        self.on_change = on_change
        self.page_size = page_size
        self.page = 1
        self.total = 0
        self.info = label(self, "", size=12, color=T.TEXT_2)
        self.info.pack(side="left")
        self.next_btn = button(self, _("Next"), "secondary", command=self.next, height=32, size=12)
        self.next_btn.pack(side="right")
        self.page_label = label(self, "", size=12, weight="semibold")
        self.page_label.pack(side="right", padx=12)
        self.prev_btn = button(self, _("Previous"), "secondary", command=self.prev, height=32, size=12)
        self.prev_btn.pack(side="right")

    @property
    def pages(self):
        return max(1, math.ceil(self.total / self.page_size))

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def update(self, total: int, shown: int):
        """Refresh the labels after a page of `shown` rows (out of `total`) was loaded."""
        self.total = total
        start = self.offset
        self.info.configure(text=_("Showing {start}-{end} of {total} records").format(
            start=start + 1 if total else 0, end=start + shown, total=total))
        self.page_label.configure(text=_("Page {page} of {pages}").format(page=self.page, pages=self.pages))
        self.prev_btn.configure(state="normal" if self.page > 1 else "disabled")
        self.next_btn.configure(state="normal" if self.page < self.pages else "disabled")

    def slice(self, rows):
        self.total = len(rows)
        self.page = min(self.page, self.pages)
        page_rows = rows[self.offset:self.offset + self.page_size]
        self.update(self.total, len(page_rows))
        return page_rows

    def reset(self):
        self.page = 1

    def prev(self):
        if self.page > 1:
            self.page -= 1
            self.on_change()

    def next(self):
        if self.page < self.pages:
            self.page += 1
            self.on_change()
