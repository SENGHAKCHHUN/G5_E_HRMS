"""Form validation for employee, department, job role and attendance entry forms.

Each function takes the raw form values (strings) and returns (data, error):
`data` is ready to send to the API when `error` is None. The server validates
everything again; this gives instant, translated feedback.
"""
from datetime import date, datetime

from core.i18n import _


def employee(values: dict, department_id: int) -> tuple[dict | None, str | None]:
    required = ("first_name", "last_name", "email", "hire_date", "salary")
    if any(not values.get(k) for k in required):
        return None, _("Please fill in all required fields.")
    if "@" not in values["email"] or "." not in values["email"].split("@")[-1]:
        return None, _("Please enter a valid email address.")
    try:
        date.fromisoformat(values["hire_date"])
        salary = int(float(values["salary"]))
    except ValueError:
        return None, _("Hire date must be YYYY-MM-DD and salary a number.")
    if salary < 0:
        return None, _("Salary cannot be negative.")
    data = {k: values[k] for k in ("first_name", "last_name", "email", "phone", "gender", "hire_date",
                                   "position", "status", "employment", "work_mode", "role")}
    data.update(salary=salary, department_id=department_id,
                shift="Remote Shift" if values.get("work_mode") == "Remote" else "Shift A")
    if "termination_date" in values:  # edit form only; the server fills in today when it is left empty
        try:
            last_day = values["termination_date"] and date.fromisoformat(values["termination_date"])
        except ValueError:
            return None, _("Last working day must be YYYY-MM-DD.")
        if last_day and last_day < date.fromisoformat(values["hire_date"]):
            return None, _("The last working day cannot be before the hire date.")
        data["termination_date"] = last_day.isoformat() if last_day and values.get("status") == "Terminated" else None
    return data, None


def department(values: dict) -> tuple[dict | None, str | None]:
    if not values.get("name"):
        return None, _("Department name is required.")
    try:
        budget = int(float(values.get("budget") or 0))
        target = int(values.get("target") or 0)
    except ValueError:
        return None, _("Budget and target must be numbers.")
    return {"name": values["name"], "lead": values.get("lead") or "-", "location": values.get("location") or "-",
            "budget": budget, "target": target, "description": values.get("description", "")}, None


def position(values: dict, department_id: int) -> tuple[dict | None, str | None]:
    if not values.get("title") or not values.get("grade"):
        return None, _("Title and pay grade are required.")
    try:
        low, high = int(float(values["min_salary"])), int(float(values["max_salary"]))
        planned = int(values.get("planned") or 0)
    except (KeyError, ValueError):
        return None, _("Salary range and headcount must be numbers.")
    if low > high:
        return None, _("Min salary cannot exceed max salary.")
    return {"department_id": department_id, "title": values["title"], "grade": values["grade"],
            "min_salary": low, "max_salary": high, "planned": planned, "skills": values.get("skills", "")}, None


def manual_attendance(values: dict, employee_id: int | None) -> tuple[dict | None, str | None]:
    if employee_id is None:
        return None, _("Unknown employee ID.")
    try:
        day = date.fromisoformat(values["date"])
        cin = datetime.strptime(values["check_in"], "%H:%M").strftime("%H:%M:%S") if values.get("check_in") else None
        cout = datetime.strptime(values["check_out"], "%H:%M").strftime("%H:%M:%S") \
            if values.get("check_out") else None
    except (KeyError, ValueError):
        return None, _("Use YYYY-MM-DD for the date and HH:MM for times.")
    if values.get("status") == "Absent":
        cin = cout = None
    if cin and cout and cout < cin:
        return None, _("Check-out cannot be before check-in.")
    return {"employee_id": employee_id, "date": day.isoformat(), "check_in": cin, "check_out": cout,
            "status": values.get("status", "On Time")}, None


def password_change(new: str, confirm: str) -> str | None:
    if new != confirm:
        return _("The new passwords do not match.")
    if len(new) < 8:
        return _("Use at least 8 characters.")
    if new.isdigit() or new.isalpha():
        return _("Use both letters and numbers.")
    return None


def payroll_line(values: dict) -> tuple[dict | None, str | None]:
    """Bonus (0 or more), adjustment (+ earning / - deduction) and note of a payroll line."""
    try:
        bonus = float(values.get("bonus") or 0)
        adjustment = float(values.get("adjustment") or 0)
    except ValueError:
        return None, _("Bonus and adjustment must be numbers.")
    if bonus < 0:
        return None, _("Bonus cannot be negative. Use a negative adjustment for a deduction.")
    return {"bonus": bonus, "adjustment": adjustment, "note": values.get("note", "")[:200]}, None
