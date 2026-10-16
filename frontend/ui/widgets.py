"""Reusable CustomTkinter components implementing the Slate Desktop System."""
import math
import tkinter as tk

import customtkinter as ctk

from core.i18n import _
from logic import formatting

from . import theme as T
from .icons import icon, logo_image

money = formatting.money  # shared money formatter, available to the views as W.money

# ------------------------------------------------------------------- basics


def label(master, text="", size=13, weight="normal", color=T.TEXT, mono=False, **kw):
    f = T.mono(size, weight) if mono else T.font(size, weight)
    kw.setdefault("anchor", "w")
    return ctk.CTkLabel(master, text=text, font=f, text_color=color, **kw)


def micro(master, text, color=T.TEXT_2, **kw):
    """Uppercase micro-label (label-sm)."""
    return label(master, text.upper(), size=11, weight="semibold", color=color, **kw)


def card(master, fg=T.SURFACE, border=True, radius=T.RADIUS_CARD, **kw):
    return ctk.CTkFrame(master, fg_color=fg, corner_radius=radius,
                        border_width=1 if border else 0, border_color=T.BORDER, **kw)


def transparent(master, **kw):
    # empty CTkFrames request 200x200 by default; collapse them instead
    kw.setdefault("width", 1)
    kw.setdefault("height", 1)
    return ctk.CTkFrame(master, fg_color="transparent", corner_radius=0, **kw)


def divider(master, vertical=False):
    if vertical:
        return ctk.CTkFrame(master, width=1, fg_color=T.BORDER, corner_radius=0)
    return ctk.CTkFrame(master, height=1, fg_color=T.BORDER, corner_radius=0)


def _btn_style(kind):
    # built on each call so a changed accent colour (theme.apply_accent) is picked up
    return {
        "primary": dict(fg_color=T.PRIMARY, hover_color=T.PRIMARY_HOVER, text_color=T.WHITE),
        "secondary": dict(fg_color=T.ELEVATED, hover_color=T.ELEVATED_HOVER, text_color=T.TEXT),
        "success": dict(fg_color=T.SUCCESS, hover_color=T.SUCCESS_HOVER, text_color=T.WHITE),
        "danger": dict(fg_color=T.DANGER, hover_color=T.DANGER_HOVER, text_color=T.WHITE),
        "danger_soft": dict(fg_color=T.BADGE["danger"][0], hover_color=T.DANGER,
                            text_color=T.BADGE["danger"][1]),
        "ghost": dict(fg_color="transparent", hover_color=T.ELEVATED, text_color=T.TEXT_2),
        "link": dict(fg_color="transparent", hover_color=T.SURFACE_ALT, text_color=T.PRIMARY),
        "soft": dict(fg_color=T.PRIMARY_SOFT, hover_color=T.ELEVATED_HOVER, text_color=T.PRIMARY),
    }[kind]


def _icon_color(kind):
    return {"primary": T.WHITE, "success": T.WHITE, "danger": T.WHITE, "secondary": T.TEXT,
            "danger_soft": T.BADGE["danger"][1], "ghost": T.TEXT_2, "link": T.PRIMARY,
            "soft": T.PRIMARY}[kind]


def button(master, text="", kind="primary", icon_name=None, command=None, height=36,
           width=None, size=13, **kw):
    style = _btn_style(kind)
    style.update(kw)
    img = icon(icon_name, 14, _icon_color(kind)) if icon_name else None
    if width is None:
        width = 36 if not text else 0
    return ctk.CTkButton(master, text=text, image=img, compound="left", command=command,
                         height=height, width=width, corner_radius=T.RADIUS_BTN,
                         font=T.font(size, "semibold"), border_spacing=6, **style)


def icon_button(master, icon_name, command=None, kind="secondary", size=32, fallback="•"):
    img = icon(icon_name, 15, _icon_color(kind))
    style = _btn_style(kind)
    return ctk.CTkButton(master, text="" if img else fallback, image=img, command=command,
                         width=size, height=size, corner_radius=T.RADIUS_BTN,
                         font=T.font(13), border_spacing=0, **style)


def badge(master, text, kind="neutral", dot=True, size=11):
    bg, fg = T.BADGE[kind]
    return ctk.CTkLabel(master, text=("● " if dot else "") + text, fg_color=bg, text_color=fg,
                        corner_radius=6, font=T.font(size, "semibold"), height=22, padx=8)


def tag(master, text, kind="neutral", mono=False):
    bg, fg = T.BADGE[kind]
    return ctk.CTkLabel(master, text=text, fg_color=bg, text_color=fg, corner_radius=6,
                        font=T.mono(12) if mono else T.font(11, "semibold"), height=24, padx=8)


def avatar(master, first="", last="", size=34, color=None, text=None):
    initials = text or ((first[:1] + last[:1]).upper() or "?")
    if color is None:
        color = T.AVATAR_COLORS[(sum(map(ord, first + last))) % len(T.AVATAR_COLORS)]
    return ctk.CTkLabel(master, text=initials, width=size, height=size, fg_color=color,
                        corner_radius=8, text_color=T.WHITE, font=T.font(max(10, size // 3), "bold"))


def icon_tile(master, icon_name, kind="info", size=40, icon_size=18):
    bg, fg = T.BADGE[kind]
    img = icon(icon_name, icon_size, fg)
    return ctk.CTkLabel(master, text="" if img else "■", image=img, width=size, height=size,
                        fg_color=bg, text_color=fg, corner_radius=8)


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


# ------------------------------------------------------------ page building


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


# -------------------------------------------------------------------- table


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


# ------------------------------------------------------------------- charts


def donut_chart(master, values, colors, center_text="", size=120, bg=T.SURFACE):
    """Matplotlib donut embedded in Tk; falls back to a plain label if unavailable."""
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except ImportError:
        return label(master, center_text, size=20, weight="bold")

    dpi = 100
    fig = Figure(figsize=(size / dpi, size / dpi), dpi=dpi)
    fig.patch.set_facecolor(T.pick(bg))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.pie(values, colors=[T.pick(c) for c in colors], startangle=90, counterclock=False,
           wedgeprops={"width": 0.22, "edgecolor": T.pick(bg), "linewidth": 2})
    ax.set_aspect("equal")
    ax.text(0, 0, center_text, ha="center", va="center", fontsize=13, fontweight="bold",
            color=T.pick(T.TEXT))
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    w = canvas.get_tk_widget()
    w.configure(highlightthickness=0, bd=0, bg=T.pick(bg))
    return w


# ------------------------------------------------------------ dialogs / toast


def _set_window_icon(win):
    try:
        from PIL import ImageTk
        img = ImageTk.PhotoImage(logo_image(32))
        win._icon_ref = img  # keep a reference
        win.iconphoto(False, img)
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


class Modal(ctk.CTkToplevel):
    """Centered modal window with a header, scrollable body and a footer bar."""

    def __init__(self, master, title, subtitle="", width=540, height=640, scroll=True):
        super().__init__(master)
        root = master.winfo_toplevel()
        self.title(title)
        self.configure(fg_color=T.SURFACE)
        self.resizable(False, False)
        self.transient(root)
        root.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - width) // 2
        y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        self._jobs = [self.after(250, lambda: _set_window_icon(self)),  # CTkToplevel resets icon ~200ms
                      self.after(50, self._grab)]

        head = transparent(self)
        head.pack(fill="x", padx=24, pady=(20, 12))
        label(head, title, size=18, weight="bold").pack(anchor="w")
        if subtitle:
            label(head, subtitle, size=12, color=T.TEXT_2).pack(anchor="w", pady=(2, 0))
        divider(self).pack(fill="x")

        self.footer = ctk.CTkFrame(self, fg_color=T.SURFACE_ALT, corner_radius=0, height=64)
        self.footer.pack(side="bottom", fill="x")
        divider(self).pack(side="bottom", fill="x")
        if scroll:
            self.body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                               scrollbar_button_color=T.ELEVATED)
        else:
            self.body = transparent(self)
        self.body.pack(fill="both", expand=True, padx=12, pady=8)

    def _grab(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass

    def destroy(self):
        for job in self._jobs:
            try:
                self.after_cancel(job)
            except (tk.TclError, ValueError):
                pass
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()

    def add_button(self, text, kind="secondary", command=None, icon_name=None):
        b = button(self.footer, text, kind=kind, command=command, icon_name=icon_name, height=38)
        b.pack(side="right", padx=(0, 12), pady=13)
        return b


class Form:
    """Two-column form builder inside a modal body."""

    def __init__(self, master, columns=2):
        self.frame = transparent(master)
        self.frame.pack(fill="x", padx=12, pady=4)
        self.cols = columns
        for i in range(columns):
            self.frame.grid_columnconfigure(i, weight=1, uniform="form")
        self.fields = {}
        self._i = 0

    def _place(self, key, text, widget_factory, span=1):
        if self._i % self.cols + span > self.cols:
            self._i += self.cols - self._i % self.cols
        r, c = divmod(self._i, self.cols)
        box = transparent(self.frame)
        box.grid(row=r, column=c, columnspan=span, sticky="ew", padx=8, pady=6)
        label(box, text, size=12, weight="semibold", color=T.TEXT_2).pack(anchor="w", pady=(0, 4))
        widget = widget_factory(box)
        widget.pack(fill="x")
        self._i += span
        return widget

    def entry(self, key, text, value="", placeholder="", span=1, show=None):
        w = self._place(key, text, lambda m: entry(m, placeholder, show=show) if show
                        else entry(m, placeholder), span)
        if value != "" and value is not None:
            w.insert(0, str(value))
        self.fields[key] = ("entry", w)
        return w

    def option(self, key, text, values, value=None, span=1, command=None, labels=None):
        """labels: {value: shown text} to display translated choices while keeping the real values."""
        labels = labels or {}
        shown = [labels.get(v, v) for v in values]
        reverse = {labels.get(v, v): v for v in values}
        current = value if value is not None else (values[0] if values else "")
        var = tk.StringVar(value=labels.get(current, current))
        on_pick = (lambda choice: command(reverse.get(choice, choice))) if command else None
        w = self._place(key, text, lambda m: option_menu(m, shown, variable=var, command=on_pick), span)
        self.fields[key] = ("var", var, reverse)
        return w

    def textbox(self, key, text, value="", span=2, height=90):
        w = self._place(key, text, lambda m: ctk.CTkTextbox(
            m, height=height, corner_radius=T.RADIUS_INPUT, border_width=1, border_color=T.BORDER,
            fg_color=T.INPUT, text_color=T.TEXT, font=T.font(13)), span)
        if value:
            w.insert("1.0", value)
        self.fields[key] = ("text", w)
        return w

    def custom(self, text, factory, span=1):
        return self._place(None, text, factory, span)

    def values(self):
        out = {}
        for k, (kind, w, *extra) in self.fields.items():
            if kind == "entry":
                out[k] = w.get().strip()
            elif kind == "var":
                reverse = extra[0] if extra else {}
                out[k] = reverse.get(w.get(), w.get())
            else:
                out[k] = w.get("1.0", "end").strip()
        return out


def confirm(master, title, message, ok_text=None, kind="danger") -> bool:
    result = {"ok": False}
    dlg = Modal(master, title, width=420, height=230, scroll=False)
    label(dlg.body, message, size=13, color=T.TEXT_2, wraplength=360, justify="left").pack(
        anchor="w", padx=14, pady=10)

    def ok():
        result["ok"] = True
        dlg.destroy()

    dlg.add_button(ok_text or _("Confirm"), kind, ok)
    dlg.add_button(_("Cancel"), "secondary", dlg.destroy)
    dlg.wait_window()
    return result["ok"]


def info_dialog(master, title, message, width=440, height=260):
    dlg = Modal(master, title, width=width, height=height, scroll=False)
    label(dlg.body, message, size=13, color=T.TEXT_2, wraplength=width - 70, justify="left").pack(
        anchor="w", padx=14, pady=10)
    dlg.add_button(_("Close"), "primary", dlg.destroy)
    return dlg


def toast(widget, text, kind="success", ms=2600):
    """Small notification in the bottom-right corner of the window."""
    root = widget.winfo_toplevel()
    bg, fg = T.BADGE[kind]
    box = ctk.CTkFrame(root, fg_color=T.SURFACE, corner_radius=10, border_width=1, border_color=fg)
    glyph = {"success": "check", "danger": "warning", "warning": "warning"}.get(kind, "info")
    img = icon(glyph, 16, fg)
    ctk.CTkLabel(box, text="" if img else "●", image=img, text_color=fg).pack(side="left", padx=(14, 8), pady=12)
    label(box, text, size=13, weight="semibold").pack(side="left", padx=(0, 16), pady=12)
    box.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
    box.lift()
    root.after(ms, box.destroy)
