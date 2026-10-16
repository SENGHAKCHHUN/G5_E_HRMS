"""System Master Clock card (clock in / clock out) used on the Attendance & Time screen.

The backend decides whether a punch is allowed (office network, check-in window) and
records the time from its own clock; this card shows the server time and explains
why the buttons are disabled when a rule blocks this device.
"""
from datetime import date, datetime, timedelta

import customtkinter as ctk

from core import i18n, tasks
from core.api_client import api
from core.i18n import _
from core.state import state
from logic import attendance as A
from logic import labels
from logic.formatting import duration
from ui import theme as T
from ui import widgets as W
from ui.icons import icon


def _load_card_data(employee_id: int, need_shift: bool) -> dict:
    """Runs in the background: everything the card shows, in one go."""
    data = {"policy": api.get_policy(), "record": api.today_record(),
            "summary": api.attendance_summary(month=date.today().strftime("%Y-%m"))}
    if need_shift:
        data["shift"] = api.get_employee(employee_id)["shift"]
    return data


class ClockCard(ctk.CTkFrame):
    def __init__(self, master, app, on_change=None):
        super().__init__(master, fg_color=T.SURFACE, corner_radius=T.RADIUS_CARD, border_width=1,
                         border_color=T.BORDER)
        self.app = app
        self.emp_id = state.session["employee_id"]
        self.shift: str | None = None
        self.on_change = on_change
        self._job = None
        self._ticks = 0
        self.offset = timedelta(0)  # server clock - local clock
        self.policy: dict = {}
        self.record: dict | None = None

        # full-width rule hint along the bottom (packed first so it spans the card)
        self.hint = W.label(self, _("Loading..."), size=12, color=T.TEXT_3, wraplength=900, justify="left")
        self.hint.pack(side="bottom", fill="x", padx=18, pady=(0, 12))

        well = ctk.CTkFrame(self, fg_color=T.INPUT, corner_radius=T.RADIUS_BTN)
        well.pack(side="left", padx=16, pady=16)
        W.micro(well, _("System Master Clock")).pack(anchor="w", padx=16, pady=(12, 0))
        row = W.transparent(well)
        row.pack(anchor="w", padx=16, pady=(0, 10))
        self.time_lbl = W.label(row, "", size=30, weight="bold", color=T.PRIMARY)
        self.time_lbl.pack(side="left")
        self.ampm = W.label(row, "", size=12, weight="semibold", color=T.TEXT_2)
        self.ampm.pack(side="left", padx=(4, 0), pady=(12, 0))

        # packed before the metrics so the buttons always keep their full width
        btns = W.transparent(self)
        btns.pack(side="right", padx=16)
        self.out_btn = W.button(btns, _("CLOCK OUT"), "danger", "stop", self.clock_out, height=42, width=130)
        self.out_btn.pack(side="right", padx=(8, 0))
        self.in_btn = W.button(btns, _("CLOCK IN"), "success", "play", self.clock_in, height=42, width=130)
        self.in_btn.pack(side="right")
        self._enable(self.in_btn, False)
        self._enable(self.out_btn, False)

        status = W.transparent(self)
        status.pack(side="left", padx=12)
        W.micro(status, _("Attendance Status")).pack(anchor="w")
        self.status_lbl = ctk.CTkLabel(status, text="…", corner_radius=8, height=34, padx=12,
                                       font=T.font(14, "semibold"))
        self.status_lbl.pack(anchor="w", pady=(6, 0))

        self.elapsed = self._metric(_("Active Elapsed"))
        self.rate = self._metric(_("Monthly Rate"), color=T.SUCCESS)

        self.refresh()
        self._tick()

    def _metric(self, title, color=T.TEXT):
        box = W.transparent(self)
        box.pack(side="left", padx=12)
        W.micro(box, title).pack(anchor="w")
        lbl = W.label(box, "--", size=22, weight="bold", color=color)
        lbl.pack(anchor="w")
        return lbl

    # ---------------------------------------------------------------- data
    def refresh(self):
        tasks.run(self, _load_card_data, self.emp_id, self.shift is None, on_done=self._render)

    def _render(self, data: dict):
        self.policy = data["policy"]
        self.record = data["record"]
        self.shift = data.get("shift", self.shift)
        server = datetime.strptime(self.policy["server_time"], "%Y-%m-%d %H:%M:%S")
        self.offset = server - datetime.now()
        summary = data["summary"]
        self.rate.configure(text=f"{A.punctuality(summary):.1f}%" if summary["worked_days"] else "--")

        network_ok, window_open = self.policy["network_ok"], self.policy["window_open"]
        rec = self.record
        if rec and rec.get("check_in") and not rec.get("check_out"):
            text = _("Clocked In at {time}").format(time=i18n.format_time(rec["check_in"]))
            text, kind = f"●  {text}  •  {labels.show(labels.SHIFT, self.shift or '')}", "success"
            self._enable(self.in_btn, False)
            self._enable(self.out_btn, network_ok)
        elif rec and rec.get("check_out"):
            text, kind = "●  " + _("Clocked Out at {time}").format(time=i18n.format_time(rec["check_out"])), "info"
            self._enable(self.in_btn, False)
            self._enable(self.out_btn, False)
        elif rec and rec.get("status") == "On Leave":
            text, kind = "●  " + _("On Approved Leave"), "neutral"
            self._enable(self.in_btn, False)
            self._enable(self.out_btn, False)
        else:
            text, kind = "●  " + _("Not Clocked In"), "warning"
            self._enable(self.in_btn, network_ok and window_open and self.policy.get("work_day", True))
            self._enable(self.out_btn, False)
        bg, fg = T.BADGE[kind]
        self.status_lbl.configure(text=text, fg_color=bg, text_color=fg)
        self._show_hint(bool(rec and rec.get("check_in")))

    def _show_hint(self, clocked_in: bool):
        p = self.policy
        window = _("Check-in {open}–{close} (server time)").format(open=p["checkin_open"], close=p["checkin_close"])
        if not p["network_ok"]:
            text, color = "✕  " + _("This device ({ip}) is not on the office network, so clock in/out is disabled. "
                                    "Ask HR for a manual entry if you are working elsewhere.").format(ip=p["ip"]), \
                T.DANGER
        elif not p.get("work_day", True) and not clocked_in:
            text, color = "⏱  " + _("Today is not a working day.") + f"  {window}.", T.WARNING
        elif not p["window_open"] and not clocked_in:
            text, color = "⏱  " + _("Check-in is closed right now.") + f"  {window}.", T.WARNING
        elif p["remote_exempt"]:
            text, color = "✓  " + _("Remote employee: you may clock in from anywhere.") + f"  {window}.", T.SUCCESS
        elif p["restrict_network"]:
            text, color = "✓  " + _("Office network ({ip}).").format(ip=p["ip"]) + f"  {window}.  " + \
                _("Times are recorded by the server."), T.SUCCESS
        else:
            text, color = f"✓  {window}.  " + _("Times are recorded by the server."), T.SUCCESS
        self.hint.configure(text=text, text_color=color)

    def _enable(self, btn, on: bool):
        """Disabled buttons turn neutral grey so they read clearly as unavailable."""
        color, hover, ic = ((T.SUCCESS, T.SUCCESS_HOVER, "play") if btn is self.in_btn
                            else (T.DANGER, T.DANGER_HOVER, "stop"))
        # CTk's disabled state drops the label on some versions, so we style it by hand
        btn.enabled = on
        btn.configure(fg_color=color if on else T.ELEVATED, hover_color=hover if on else T.ELEVATED,
                      text_color=T.WHITE if on else T.TEXT_3, cursor="hand2" if on else "arrow",
                      image=icon(ic, 14, T.WHITE if on else T.TEXT_3))

    def _tick(self):
        now = datetime.now() + self.offset  # show the server's clock: it is what gets recorded
        self._ticks += 1
        if self._ticks % 60 == 0:  # re-check the rules every minute (window may open/close)
            self.refresh()
        self.time_lbl.configure(text=f"{now.hour % 12 or 12:02d}:{now:%M:%S}")
        self.ampm.configure(text=i18n.am_pm(now.hour))
        rec = self.record
        if rec and rec.get("check_in"):
            self.elapsed.configure(text=duration(A.worked_seconds(rec, now)))
        else:
            self.elapsed.configure(text=duration(0))
        self._job = self.after(1000, self._tick)

    # ------------------------------------------------------------- actions
    def clock_in(self):
        if getattr(self.in_btn, "enabled", True):
            tasks.run(self, api.check_in, on_done=lambda rec: self._after_change(
                _("Clocked in at {time}").format(time=i18n.format_time(rec["check_in"]))
                + (" " + _("(late)") if rec["status"] == "Late" else "")))

    def clock_out(self):
        if getattr(self.out_btn, "enabled", True):
            tasks.run(self, api.check_out, on_done=lambda rec: self._after_change(
                _("Clocked out at {time}").format(time=i18n.format_time(rec["check_out"]))))

    def _after_change(self, msg: str):
        self.refresh()
        W.toast(self, msg)
        self.app.invalidate("dashboard", "leave")
        if self.on_change:
            self.on_change()

    def destroy(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()
