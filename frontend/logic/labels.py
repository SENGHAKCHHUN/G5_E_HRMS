"""Translated display names for values stored in English (statuses, roles, types...).

The server always stores and expects the English values; only what is shown changes.
"""
from core.i18n import N_, _

EMPLOYEE_STATUS = {"Active": N_("Active"), "Probation": N_("Probation"), "On Leave": N_("On Leave"),
                   "Terminated": N_("Terminated")}
EMPLOYMENT = {"Full-time": N_("Full-time"), "Part-time": N_("Part-time"), "Contractor": N_("Contractor")}
WORK_MODE = {"HQ Onsite": N_("HQ Onsite"), "Hybrid": N_("Hybrid"), "Remote": N_("Remote")}
GENDER = {"Male": N_("Male"), "Female": N_("Female"), "Other": N_("Other")}
ROLE = {"Admin": N_("Admin"), "HR Manager": N_("HR Manager"), "Employee": N_("Employee")}
PAYROLL_STATUS = {"Pending": N_("Pending"), "Calculated": N_("Calculated"), "Paid": N_("Paid")}
REQUISITION_STATUS = {"Open": N_("Open"), "Filled": N_("Filled"), "Cancelled": N_("Cancelled")}
SHIFT = {"Shift A": N_("Shift A"), "Remote Shift": N_("Remote Shift")}
WEEKDAYS = {"Mon": N_("Mon"), "Tue": N_("Tue"), "Wed": N_("Wed"), "Thu": N_("Thu"), "Fri": N_("Fri"),
            "Sat": N_("Sat"), "Sun": N_("Sun")}


def show(mapping: dict, value: str | None) -> str:
    """Translated label for a stored value (unknown values are shown as they are)."""
    return _(mapping[value]) if value in mapping else str(value)


def choices(mapping: dict) -> dict:
    """{stored value: translated label} for a form's option menu."""
    return {k: _(v) for k, v in mapping.items()}
