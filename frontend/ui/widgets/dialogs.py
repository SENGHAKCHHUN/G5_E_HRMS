"""Windows on top of the app: modal dialog, two-column form, confirm, info dialog, toast."""
import tkinter as tk

import customtkinter as ctk

from core.i18n import _

from .. import theme as T
from ..icons import icon, logo_image

from .basics import label, transparent, divider, button
from .inputs import entry, option_menu


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
