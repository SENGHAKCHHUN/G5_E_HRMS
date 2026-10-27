"""Demo data for an empty database (used by seed.py).

A small company: one department with 7 positions and 7 employees (3 of them can sign
in), about two months of attendance, a few leave requests and an audit trail. Generated
deterministically (fixed random seed) and anchored to today's date, so the "today"
screens always have data. Payroll is not stored here: seed.py calculates last month's
payroll with the real payroll rules and marks it paid.
"""
import random
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta

from .core.security import DEMO_PASSWORDS

TODAY = date.today()
_rng = random.Random(42)

# --------------------------------------------------------------- department
DEPARTMENTS = [
    {"id": 1, "name": "Head Office", "code": "HQ-01", "lead": "Dara Chan", "location": "Phnom Penh",
     "description": "Management, people, finance, sales and product, all in one office.",
     "budget": 12_000, "target": 8, "icon": "department"},
]

# ----------------------------------------------------------------- positions
# (title, grade, min, max, skills, planned headcount)
_POSITIONS = [
    ("General Manager", "M-5", 2200, 3000, "Leadership, Strategy, Budgeting", 1),
    ("HR Manager", "H-4", 1200, 1800, "Employee Relations, Policy, Payroll", 1),
    ("HR Assistant", "H-2", 500, 750, "Onboarding, Records, Scheduling", 1),
    ("Accountant", "F-3", 900, 1300, "Bookkeeping, Tax, Reconciliation", 1),
    ("Software Developer", "E-3", 1000, 1600, "Python, SQL, Desktop Apps", 2),
    ("Sales Executive", "S-2", 700, 1100, "Customer Care, Negotiation, CRM", 1),
    ("Office Assistant", "A-1", 350, 550, "Reception, Purchasing, Filing", 1),
]
POSITIONS = [
    {"id": i + 1, "department_id": 1, "title": t, "grade": g, "min_salary": lo, "max_salary": hi,
     "skills": s, "planned": n}
    for i, (t, g, lo, hi, s, n) in enumerate(_POSITIONS)
]

# ----------------------------------------------------------------- employees
# (first, last, gender, position, salary, days since hire, status, work mode)
_PEOPLE = [
    ("Dara", "Chan", "Male", "General Manager", 2500, 2900, "Active", "HQ Onsite"),
    ("Sophea", "Lim", "Female", "HR Manager", 1500, 1800, "Active", "HQ Onsite"),
    ("Sokha", "Chea", "Female", "Software Developer", 1300, 900, "Active", "Hybrid"),
    ("Vannak", "Sok", "Male", "Accountant", 1100, 1300, "Active", "HQ Onsite"),
    ("Chenda", "Kim", "Female", "Sales Executive", 900, 600, "Active", "HQ Onsite"),
    ("Rithy", "Mao", "Male", "Office Assistant", 450, 40, "Probation", "HQ Onsite"),
    ("Bopha", "Ny", "Female", "HR Assistant", 600, 500, "On Leave", "HQ Onsite"),
]
EMPLOYEES = [
    {"id": i, "code": f"EMP-{i:03d}", "first_name": first, "last_name": last,
     "email": f"{first[0].lower()}.{last.lower()}@workflow.io", "phone": f"+855 12 {300 + i * 11:03d} {400 + i * 7:03d}",
     "gender": gender, "hire_date": (TODAY - timedelta(days=days)).isoformat(), "position": title,
     "position_id": next(p["id"] for p in POSITIONS if p["title"] == title), "salary": salary, "department_id": 1,
     "status": status, "employment": "Full-time", "work_mode": mode,
     "shift": "Remote Shift" if mode == "Remote" else "Shift A"}
    for i, (first, last, gender, title, salary, days, status, mode) in enumerate(_PEOPLE, start=1)
]


def _find(first: str) -> dict:
    return next(e for e in EMPLOYEES if e["first_name"] == first)


# --------------------------------------------------------------------- users
USERS = [
    {"id": 1, "username": "admin", "password": DEMO_PASSWORDS["admin"], "role": "Admin",
     "employee_id": _find("Dara")["id"]},
    {"id": 2, "username": "hr", "password": DEMO_PASSWORDS["hr"], "role": "HR Manager",
     "employee_id": _find("Sophea")["id"]},
    {"id": 3, "username": "employee", "password": DEMO_PASSWORDS["employee"], "role": "Employee",
     "employee_id": _find("Sokha")["id"]},
]

# --------------------------------------------------------------------- leave
FIRST_DAY = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)  # first day of last month


def _weekday(d: date) -> date:
    """The same day, or the next Monday when it falls on a weekend."""
    return d + timedelta(days=(7 - d.weekday()) % 7) if d.weekday() >= 5 else d


def _leave(lid, first, typ, start, days, reason, status, note=""):
    start = _weekday(start)
    end = start
    for _ in range(days - 1):  # `days` working days long
        end = _weekday(end + timedelta(days=1))
    return {"id": lid, "employee_id": _find(first)["id"], "type": typ, "start_date": start.isoformat(),
            "end_date": end.isoformat(), "reason": reason, "status": status, "review_note": note}


LEAVE_REQUESTS = [
    _leave(1001, "Sokha", "Annual", FIRST_DAY + timedelta(days=9), 3, "Family trip to Siem Reap.", "Approved"),
    _leave(1002, "Chenda", "Unpaid", FIRST_DAY + timedelta(days=16), 2, "Personal matter in the province.",
           "Approved"),
    _leave(1003, "Vannak", "Casual", TODAY - timedelta(days=12), 1, "Bank appointment.", "Rejected",
           "Month-end closing that day, please choose another date."),
    _leave(1004, "Bopha", "Annual", TODAY - timedelta(days=1), 4, "Pchum Ben holiday with family.", "Approved"),
    _leave(1005, "Sokha", "Casual", TODAY + timedelta(days=14), 1, "Moving to a new apartment.", "Pending"),
    _leave(1006, "Rithy", "Sick", TODAY + timedelta(days=3), 1, "Dentist appointment.", "Pending"),
]


def _on_leave(emp_id: int, day: date) -> bool:
    return any(lv["employee_id"] == emp_id and lv["status"] == "Approved"
               and lv["start_date"] <= day.isoformat() <= lv["end_date"] for lv in LEAVE_REQUESTS)


# ---------------------------------------------------------------- attendance
SHIFT_START = time(9, 0)
SHIFT_END = time(18, 0)
GRACE_MINUTES = 15


def _workdays() -> Iterator[date]:
    """Monday to Friday from the first day of last month up to today."""
    d = FIRST_DAY
    while d <= TODAY:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def _make_attendance():
    records, now = [], datetime.now()
    for day in _workdays():
        for emp in EMPLOYEES:
            if day < date.fromisoformat(emp["hire_date"]):
                continue
            if _on_leave(emp["id"], day):
                records.append({"employee_id": emp["id"], "date": day.isoformat(), "check_in": None,
                                "check_out": None, "status": "On Leave"})
                continue
            r = _rng.random()
            if r < 0.03:
                records.append({"employee_id": emp["id"], "date": day.isoformat(), "check_in": None,
                                "check_out": None, "status": "Absent"})
                continue
            late = r < 0.09
            minutes = _rng.randint(16, 40) if late else _rng.randint(-20, 10)
            cin = datetime.combine(day, SHIFT_START) + timedelta(minutes=minutes, seconds=_rng.randint(0, 59))
            stay = _rng.randint(90, 120) if r > 0.92 else _rng.randint(-10, 30)  # some stay for overtime
            cout = datetime.combine(day, SHIFT_END) + timedelta(minutes=stay)
            status = "Late" if minutes > GRACE_MINUTES else "On Time"
            if 0.09 <= r < 0.11:
                status, cout = "Half Day", cin + timedelta(hours=3, minutes=_rng.randint(0, 50))
            if day == TODAY:
                if cin > now:
                    continue  # not in yet
                if cout > now:
                    cout = None  # still at work
            records.append({"employee_id": emp["id"], "date": day.isoformat(),
                            "check_in": cin.strftime("%H:%M:%S"),
                            "check_out": cout.strftime("%H:%M:%S") if cout else None, "status": status})
    return records


ATTENDANCE = _make_attendance()

# ----------------------------------------------------------------- audit log
AUDIT_LOG = [
    ((TODAY, "08:55"), "hr", "LOGIN", "Successful sign-in from 192.168.1.20"),
    ((TODAY - timedelta(days=1), "16:40"), "hr", "APPROVE", "Leave LV-1004 approved"),
    ((TODAY - timedelta(days=12), "10:05"), "hr", "REJECT", "Leave LV-1003 rejected"),
    ((TODAY - timedelta(days=40), "09:30"), "admin", "CREATE", "Employee EMP-006 Rithy Mao (login 'r.mao')"),
]
