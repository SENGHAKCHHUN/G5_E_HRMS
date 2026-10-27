"""Settings sections: company & workplace profile, appearance."""
from datetime import datetime

import customtkinter as ctk

from core import prefs
from core.i18n import _
from core.state import state
from logic import labels
from ui import theme as T
from ui import widgets as W


DAYS = list(labels.WEEKDAYS)


TIMEZONES = ["(UTC+07:00) Bangkok, Hanoi, Phnom Penh", "(UTC+08:00) Singapore, Kuala Lumpur",
             "(UTC+00:00) London, Dublin", "(UTC-05:00) Eastern Time (US & Canada)",
             "(UTC-08:00) Pacific Time (US & Canada)"]


def _shift_hours(start: str, end: str) -> float:
    try:
        diff = datetime.strptime(end, "%H:%M") - datetime.strptime(start, "%H:%M")
    except ValueError:
        return 8.0
    return max(0.0, diff.total_seconds() / 3600)


class GeneralSections:
    """Settings sections: company & workplace profile, appearance."""

    def _sec_general(self):
        b = self._section(_("Company & Workplace Profile"),
                          _("Used on payslip headers, reports and email"), "org")
        self._field(b, "company_name", _("Company Name"), 0, 0)
        self._field(b, "domain", _("Company Domain"), 0, 1)
        self._option(b, "timezone", _("Operational Timezone"), TIMEZONES, 1, 0, span=2)

        week = ctk.CTkFrame(b, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        week.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        top = W.transparent(week)
        top.pack(fill="x", padx=14, pady=(12, 8))
        W.label(top, _("Work Week"), size=13, weight="semibold").pack(side="left")
        hours = W.label(top, "", size=12, color=T.TEXT_2)
        hours.pack(side="right")
        days = W.transparent(week)
        days.pack(fill="x", padx=14, pady=(0, 14))
        W.grid_columns(days, 7, uniform="days")
        selected = set(self.values.get("work_week", []))
        per_day = _shift_hours(self.values.get("shift_start", "09:00"), self.values.get("shift_end", "18:00"))
        buttons = {}

        def paint():
            for d, btn in buttons.items():
                on = d in selected
                btn.configure(fg_color=T.PRIMARY if on else T.ELEVATED,
                              text_color=T.WHITE if on else T.TEXT_2,
                              hover_color=T.PRIMARY_HOVER if on else T.ELEVATED_HOVER)
            week = round(len(selected) * per_day, 1)
            hours.configure(text=_("{hours:g} scheduled hours per week").format(hours=week))

        def flip(d):
            selected.symmetric_difference_update({d})
            paint()

        for i, d in enumerate(DAYS):
            btn = ctk.CTkButton(days, text=labels.show(labels.WEEKDAYS, d), height=36, corner_radius=T.RADIUS_BTN,
                                font=T.font(13, "semibold"), command=lambda d=d: flip(d))
            btn.grid(row=0, column=i, sticky="ew", padx=3)
            buttons[d] = btn
        paint()
        self.getters["work_week"] = lambda: [d for d in DAYS if d in selected]

    def _sec_appearance(self):
        b = self._section(_("Appearance & Theme Preferences"), _("Theme, scaling and accent colour on this computer"),
                          "palette")
        modes = {"Dark": _("Dark"), "Light": _("Light"), "System": _("System")}
        W.label(b, _("Theme Mode"), size=12, weight="semibold", color=T.TEXT_2).grid(row=0, column=0, sticky="w")
        theme = W.segmented(b, list(modes.values()), command=lambda v: self.app.set_theme(
            next(k for k, shown in modes.items() if shown == v).lower()))
        theme.set(modes.get(ctk.get_appearance_mode(), modes["Dark"]))
        theme.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        W.label(b, _("UI Scaling"), size=12, weight="semibold", color=T.TEXT_2).grid(
            row=0, column=1, sticky="w", padx=(8, 0))

        def set_scale(v):
            state.scaling = int(v[:-1]) / 100
            ctk.set_widget_scaling(state.scaling)
            prefs.save(scaling=state.scaling)
        scale = W.segmented(b, ["90%", "100%", "110%", "125%"], command=set_scale)
        scale.set(f"{round(state.scaling * 100)}%")
        scale.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))

        W.label(b, _("Accent colour"), size=12, weight="semibold", color=T.TEXT_2).grid(
            row=2, column=0, sticky="w", pady=(16, 4))
        sw = W.transparent(b)
        sw.grid(row=3, column=0, columnspan=2, sticky="w")
        for name, (primary, *_rest) in T.ACCENTS.items():
            chosen = name == state.accent
            ctk.CTkButton(sw, text="✓" if chosen else "", width=34, height=34, corner_radius=17,
                          fg_color=primary, hover_color=primary, text_color="#FFFFFF",
                          border_width=3 if chosen else 0, border_color=T.TEXT,
                          font=T.font(14, "bold"), command=lambda n=name: self._set_accent(n)).pack(
                side="left", padx=(0, 10))
        W.label(sw, _("Saved on this computer"), size=12, color=T.TEXT_2).pack(side="left", padx=6)

    def _set_accent(self, name):
        state.accent = name
        prefs.save(accent=name)
        T.apply_accent(name)
        self.app.app.rebuild("settings")  # every screen picks up the new colour
