"""Settings sections: attendance policies and check-in rules, payroll & tax."""
from core.i18n import _
from ui import theme as T
from ui import widgets as W


class PolicySections:
    """Settings sections: attendance policies and check-in rules, payroll & tax."""

    def _sec_attendance(self):
        b = self._section(_("Attendance Policies"), _("Shift schedule, grace period and overtime rules"), "clock")
        self._field(b, "shift_start", _("Shift Start (HH:MM)"), 0, 0)
        self._field(b, "shift_end", _("Shift End (HH:MM)"), 0, 1)
        self._field(b, "grace_minutes", _("Late Grace Period (minutes)"), 1, 0, cast=int)
        self._field(b, "overtime_after", _("Overtime Counted After (HH:MM)"), 1, 1)

        r = self._section(_("Check-In Rules"), _("Enforced by the server, using the server's clock"), "lock",
                          right=_("Server Enforced"))
        self._field(r, "checkin_open", _("Check-in Opens (HH:MM)"), 0, 0)
        self._field(r, "checkin_close", _("Check-in Closes (HH:MM)"), 0, 1)
        self._toggle_row(r, "restrict_network", _("Office network only"),
                         _("Clock in/out only from the networks below"), 1, 0)
        self._toggle_row(r, "remote_exempt", _("Remote staff exempt"),
                         _("Work mode 'Remote' may clock in from anywhere"), 1, 1)
        self._field(r, "office_networks", _("Office Networks (IP addresses or ranges, comma-separated)"), 2, 0,
                    span=2)
        W.label(r, _("Example: 192.168.1.0/24, 10.0.0.0/8. Forgotten or off-site punches are fixed by HR with "
                     "Manual Log Entry."), size=11, color=T.TEXT_2, wraplength=700, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w")

        d = self._section(_("Closing the Day"), _("Applied by the server once a day is over"), "calendar",
                          right=_("Server Enforced"))
        self._toggle_row(d, "auto_absent", _("Mark no-shows Absent"),
                         _("No check-in by the time check-in closes on a working day"), 0, 0)
        self._toggle_row(d, "auto_checkout", _("Close forgotten check-outs"),
                         _("Set to Shift End when nobody checked out by the next day"), 0, 1)
        self._field(d, "half_day_hours", _("Half Day Below (hours worked, 0 = off)"), 1, 0, cast=float)
        self._field(d, "checkout_cutoff", _("Late Check-out Until (next day, HH:MM)"), 1, 1)
        W.label(d, _("A check-out after midnight and before this time ends the previous day's shift. Records "
                     "made by these rules are marked 'auto' so HR can review them."), size=11, color=T.TEXT_2,
                wraplength=700, justify="left").grid(row=2, column=0, columnspan=2, sticky="w")

    def _sec_payroll(self):
        b = self._section(_("Payroll & Tax Configuration"), _("Rates applied when payroll is generated"), "payroll")
        self._field(b, "tax_rate", _("Income Tax Rate (%)"), 0, 0, cast=float)
        self._field(b, "pension_rate", _("Pension Contribution (%)"), 0, 1, cast=float)
        self._field(b, "pay_day", _("Monthly Pay Day"), 1, 0, cast=int)
        self._option(b, "currency", _("Currency"), ["USD", "KHR", "EUR", "SGD"], 1, 1)
        self._field(b, "tax_brackets", _("Progressive Tax Brackets (from:rate %, empty = flat rate above)"), 2, 0,
                    span=2)
        W.label(b, _("Example in KHR: 0:0, 1500000:5, 2000000:10, 8500000:15, 12500000:20. Each rate applies to "
                     "the part of monthly pay above its amount. Check current rates with your accountant."),
                size=11, color=T.TEXT_2, wraplength=700, justify="left").grid(row=3, column=0, columnspan=2, sticky="w")
        self._toggle_row(b, "tax_bonus", _("Tax bonus and overtime"), _("Taxed like salary (off = base salary only)"),
                         4, 0)
        self._field(b, "insurance_amount", _("Health Insurance per Month"), 5, 0, cast=float)
        self._field(b, "insurance_high_amount", _("Health Insurance (higher salaries)"), 5, 1, cast=float)
        self._field(b, "insurance_threshold", _("Higher Insurance from Base Salary"), 6, 0, cast=float)

        a = self._section(_("Attendance in Payroll"), _("Taken from attendance and leave when payroll is calculated"),
                          "clock")
        self._toggle_row(a, "deduct_unpaid", _("Deduct unpaid days"),
                         _("Absent and unpaid leave = 1 day, Half Day = 0.5 day (salary / working days)"), 0, 0)
        self._field(a, "overtime_rate", _("Overtime Pay Rate (x hourly rate, 0 = not paid)"), 0, 1, cast=float)
        W.label(a, _("Hourly rate = daily rate / shift hours (Attendance & Policies). Overtime counts after "
                     "'Overtime Counted After' and never on a Half Day."), size=11, color=T.TEXT_2, wraplength=700,
                justify="left").grid(row=1, column=0, columnspan=2, sticky="w")
