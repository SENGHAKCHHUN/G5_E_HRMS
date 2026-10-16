"""Demo data for an empty database (used by seed.py).

Generated deterministically (fixed random seed) and anchored to today's date, so
the "today" screens always have data: 148 employees in 6 departments, three
months of attendance and payroll, and a set of leave requests.
"""
import random
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta

TODAY = date.today()
_rng = random.Random(42)

# --------------------------------------------------------------- departments
DEPARTMENTS = [
    {"id": 1, "name": "Engineering", "code": "DIVISION-01", "lead": "Alex Thorne",
     "location": "Global R&D Hub", "description": "Platform, infrastructure and product engineering.",
     "budget": 320_000, "target": 56, "icon": "department"},
    {"id": 2, "name": "Product & Design", "code": "DIVISION-02", "lead": "Maya Lin",
     "location": "HQ Floor 4", "description": "Product strategy, research and UX/UI design.",
     "budget": 145_000, "target": 20, "icon": "palette"},
    {"id": 3, "name": "Sales & Marketing", "code": "DIVISION-03", "lead": "Sarah Jenkins",
     "location": "HQ Floor 2", "description": "Revenue, partnerships, brand and growth.",
     "budget": 195_000, "target": 40, "icon": "trend"},
    {"id": 4, "name": "Finance & Payroll", "code": "DIVISION-04", "lead": "Priya Natarajan",
     "location": "HQ Floor 3", "description": "Accounting, treasury and payroll operations.",
     "budget": 92_000, "target": 14, "icon": "payroll"},
    {"id": 5, "name": "People & Culture", "code": "DIVISION-05", "lead": "Jessica Gomez",
     "location": "HQ Floor 3", "description": "HR operations, talent acquisition and culture.",
     "budget": 70_000, "target": 10, "icon": "people"},
    {"id": 6, "name": "Legal & Compliance", "code": "DIVISION-06", "lead": "Robert Sterling",
     "location": "HQ Floor 5", "description": "Contracts, regulatory affairs and governance.",
     "budget": 84_000, "target": 10, "icon": "shield"},
]

# ----------------------------------------------------------------- positions
# (department_id, title, grade, min, max, skills, headcount)
_POSITIONS = [
    (1, "Lead Systems Architect", "E-5", 8500, 11000, "Distributed Infrastructure & Cloud", 3),
    (1, "Senior Backend Engineer", "E-4", 6500, 8200, "Go, Rust, Microservices Core", 18),
    (1, "Full-Stack Engineer", "E-3", 4800, 6200, "React, TypeScript, Node.js Stack", 24),
    (1, "QA & Automation Specialist", "E-2", 3800, 4900, "Playwright, CI/CD, TestOps", 9),
    (2, "Head of Product", "P-5", 8000, 10000, "Roadmaps, Strategy, Discovery", 2),
    (2, "Senior UI/UX Designer", "P-4", 5200, 6800, "Figma, Design Systems, Research", 9),
    (2, "Product Manager", "P-3", 5000, 6500, "Agile Delivery, Analytics", 11),
    (3, "Sales Director", "S-5", 7500, 9500, "Enterprise Deals, Forecasting", 2),
    (3, "SEO & Growth Lead", "S-3", 4500, 5800, "SEO, Paid Acquisition, CRO", 6),
    (3, "Account Executive", "S-3", 4200, 5600, "Pipeline, Negotiation, CRM", 18),
    (3, "Marketing Specialist", "S-2", 3600, 4600, "Content, Campaigns, Events", 8),
    (3, "Sales Ops Analyst", "S-2", 3800, 4800, "Salesforce, Reporting", 4),
    (4, "Finance Controller", "F-5", 7800, 9600, "IFRS, Audit, Treasury", 1),
    (4, "Payroll Specialist", "F-3", 4000, 5200, "Payroll Tax, Benefits", 5),
    (4, "Accountant", "F-3", 4200, 5400, "AP/AR, Reconciliation", 8),
    (5, "HR Manager", "H-4", 5500, 7000, "Employee Relations, Policy", 2),
    (5, "HR Generalist", "H-3", 4200, 5200, "Onboarding, HRIS, Benefits", 4),
    (5, "Talent Acquisition Partner", "H-3", 4300, 5400, "Sourcing, Interviewing", 4),
    (6, "Legal Counsel", "L-5", 8200, 10500, "Contracts, Corporate Law", 4),
    (6, "Compliance Analyst", "L-3", 4600, 6000, "GDPR, SOX, Risk", 6),
]
POSITIONS = [
    {"id": i + 1, "department_id": d, "title": t, "grade": g, "min_salary": lo,
     "max_salary": hi, "skills": s, "planned": n}
    for i, (d, t, g, lo, hi, s, n) in enumerate(_POSITIONS)
]

# ----------------------------------------------------------------- employees
# Named employees that appear in the designs (first_name, last_name, position title, extras)
_NAMED = [
    ("Samantha", "Reed", "Senior Backend Engineer", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("Michael", "Chen", "Senior UI/UX Designer", {"gender": "Male", "work_mode": "Hybrid"}),
    ("Jessica", "Gomez", "HR Generalist", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("Brian", "O'Connor", "SEO & Growth Lead", {"gender": "Male", "employment": "Contractor",
                                               "work_mode": "Remote", "status": "On Leave"}),
    ("Tariq", "Mansoor", "Lead Systems Architect", {"gender": "Male", "work_mode": "Remote",
                                                    "status": "Probation"}),
    ("Elena", "Rostova", "Full-Stack Engineer", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("David", "Zhao", "Head of Product", {"gender": "Male", "work_mode": "HQ Onsite"}),
    ("Alex", "Morgan", "HR Manager", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("Alex", "Thorne", "Lead Systems Architect", {"gender": "Male", "work_mode": "HQ Onsite"}),
    ("Maya", "Lin", "Head of Product", {"gender": "Female", "work_mode": "Hybrid"}),
    ("Sarah", "Jenkins", "Sales Director", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("Priya", "Natarajan", "Finance Controller", {"gender": "Female", "work_mode": "HQ Onsite"}),
    ("Robert", "Sterling", "Legal Counsel", {"gender": "Male", "work_mode": "HQ Onsite"}),
    ("Liam", "Vance", "Talent Acquisition Partner", {"gender": "Male", "work_mode": "HQ Onsite"}),
    ("Marcus", "Sterling", "Account Executive", {"gender": "Male", "work_mode": "Hybrid"}),
    ("Daniel", "Brooks", "Lead Systems Architect", {"gender": "Male", "work_mode": "HQ Onsite"}),
]

_FIRST_M = ["James", "Noah", "Ethan", "Lucas", "Mateo", "Arjun", "Kenji", "Omar", "Leo", "Ryan",
            "Hugo", "Samuel", "Victor", "Andre", "Felix", "Isaac", "Julian", "Kai", "Nathan", "Owen"]
_FIRST_F = ["Olivia", "Emma", "Ava", "Sofia", "Mia", "Aisha", "Yuki", "Chloe", "Grace", "Nora",
            "Lena", "Zara", "Hannah", "Isla", "Maria", "Ruby", "Leah", "Amara", "Ines", "Clara"]
_LAST = ["Patel", "Kim", "Nguyen", "Garcia", "Silva", "Müller", "Okafor", "Rossi", "Tanaka",
         "Hughes", "Walsh", "Novak", "Haddad", "Larsen", "Costa", "Fischer", "Ibrahim", "Moreau",
         "Bennett", "Sato", "Kowalski", "Reyes", "Andersen", "Chopra", "Dubois", "Park", "Wright"]


def _make_employees():
    slots = []  # one position title per seat
    for p in POSITIONS:
        slots += [p] * p["planned"]
    by_title = {}
    for p in slots:
        by_title.setdefault(p["title"], []).append(p)

    people = []
    used_named = set()
    for first, last, title, extra in _NAMED:
        pos = by_title[title].pop()
        slots.remove(pos)
        people.append((first, last, pos, extra))
        used_named.add((first, last))

    seen = set(used_named)
    for pos in slots:
        while True:
            gender = _rng.choice(["Male", "Female"])
            first = _rng.choice(_FIRST_M if gender == "Male" else _FIRST_F)
            last = _rng.choice(_LAST)
            if (first, last) not in seen:
                seen.add((first, last))
                break
        people.append((first, last, pos, {"gender": gender}))

    # keep the named people first, shuffle the rest so departments are mixed
    named, rest = people[:len(_NAMED)], people[len(_NAMED):]
    _rng.shuffle(rest)

    extra_leave = 5  # additional employees on leave today (Brian is the first)
    extra_probation = 3
    out = []
    used_emails = set()
    for i, (first, last, pos, extra) in enumerate(named + rest, start=1):
        status = extra.get("status", "Active")
        if i > len(_NAMED):
            if extra_leave and _rng.random() < 0.06:
                status, extra_leave = "On Leave", extra_leave - 1
            elif extra_probation and _rng.random() < 0.04:
                status, extra_probation = "Probation", extra_probation - 1
        salary = _rng.randrange(pos["min_salary"], pos["max_salary"] + 1, 50)
        local = f"{first[0].lower()}.{last.lower().replace(chr(39), '').replace('ü', 'u')}"
        if local in used_emails:  # e.g. Mia & Maria Tanaka -> m.tanaka, m.tanaka2
            n = 2
            while f"{local}{n}" in used_emails:
                n += 1
            local = f"{local}{n}"
        used_emails.add(local)
        hired = TODAY - timedelta(days=_rng.randint(60, 3200))
        if status == "Probation":
            hired = TODAY - timedelta(days=_rng.randint(20, 80))
        out.append({
            "id": i,
            "code": f"EMP-{i:03d}",
            "first_name": first,
            "last_name": last,
            "email": f"{local}@workflow.io",
            "phone": f"+1 (555) {_rng.randint(200, 989):03d}-{_rng.randint(1000, 9999)}",
            "gender": extra.get("gender", "Male"),
            "hire_date": hired.isoformat(),
            "position": pos["title"],
            "position_id": pos["id"],
            "salary": salary,
            "department_id": pos["department_id"],
            "status": status,
            "employment": extra.get("employment", "Full-time" if _rng.random() > 0.08 else "Contractor"),
            "work_mode": extra.get("work_mode", _rng.choice(["HQ Onsite", "HQ Onsite", "Hybrid", "Remote"])),
            "shift": "Remote Shift" if extra.get("work_mode") == "Remote" else "Shift A",
        })
    return out


EMPLOYEES = _make_employees()


def _find(first: str, last: str) -> dict:
    return next(e for e in EMPLOYEES if e["first_name"] == first and e["last_name"] == last)


# --------------------------------------------------------------------- users
USERS = [
    {"id": 1, "username": "admin", "password": "admin123", "role": "Admin",
     "employee_id": _find("Daniel", "Brooks")["id"]},
    {"id": 2, "username": "hr", "password": "hr123", "role": "HR Manager",
     "employee_id": _find("Alex", "Morgan")["id"]},
    {"id": 3, "username": "employee", "password": "emp123", "role": "Employee",
     "employee_id": _find("Samantha", "Reed")["id"]},
]

# ---------------------------------------------------------------- attendance
SHIFT_START = time(9, 0)
SHIFT_END = time(18, 0)
GRACE_MINUTES = 15


def _workdays(months_back: int = 2) -> Iterator[date]:
    first = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)
    if months_back == 2:
        first = (first - timedelta(days=1)).replace(day=1)
    d = first
    while d <= TODAY:
        if d.weekday() < 5 or d == TODAY:
            yield d
        d += timedelta(days=1)


def _make_attendance():
    records = []
    rid = 1
    now = datetime.now()
    for day in _workdays():
        is_today = day == TODAY
        for emp in EMPLOYEES:
            r = _rng.random()
            if emp["status"] == "On Leave" and is_today:
                records.append({"id": rid, "employee_id": emp["id"], "date": day.isoformat(),
                                "check_in": None, "check_out": None, "status": "On Leave"})
                rid += 1
                continue
            if r < 0.02:
                status, cin, cout = "Absent", None, None
            else:
                # most arrive 08:40-09:10, ~8% are late
                minutes = _rng.randint(-20, 10) if r > 0.10 else _rng.randint(16, 45)
                cin = datetime.combine(day, SHIFT_START) + timedelta(minutes=minutes, seconds=_rng.randint(0, 59))
                cout = datetime.combine(day, SHIFT_END) + timedelta(minutes=_rng.randint(-25, 45))
                status = "Late" if minutes > GRACE_MINUTES else "On Time"
                if r < 0.035:
                    status = "Half Day"
                    cout = cin + timedelta(hours=4, minutes=_rng.randint(0, 30))
                if is_today:
                    if cin > now:  # early in the day: not everyone is in yet
                        continue
                    if cout > now:
                        cout = None  # shift still running: still in the office
            records.append({
                "id": rid, "employee_id": emp["id"], "date": day.isoformat(),
                "check_in": cin.strftime("%H:%M:%S") if cin else None,
                "check_out": cout.strftime("%H:%M:%S") if cout else None,
                "status": status,
            })
            rid += 1
    return records


ATTENDANCE = _make_attendance()

# --------------------------------------------------------------------- leave
LEAVE_TYPES = ["Annual", "Sick", "Casual", "Maternity/Paternity", "Unpaid"]
LEAVE_ALLOWANCE = {"Annual": 20, "Sick": 10, "Casual": 5}


def _make_leaves():
    rows = [
        ("David", "Zhao", "Annual", 30, 34, "Family trip planned months ahead.", "Pending"),
        ("Liam", "Vance", "Casual", 6, 6, "Moving apartments.", "Pending"),
        ("Maya", "Lin", "Annual", 12, 16, "Conference + vacation.", "Pending"),
        ("Marcus", "Sterling", "Sick", 1, 1, "Dentist appointment.", "Pending"),
        ("Elena", "Rostova", "Sick", -9, -8, "Flu, doctor's note attached.", "Approved"),
        ("Brian", "O'Connor", "Annual", -1, 4, "Annual leave.", "Approved"),
        ("Brian", "O'Connor", "Casual", -13, -12, "Personal errand.", "Rejected"),
        ("Samantha", "Reed", "Annual", -40, -36, "Summer holiday.", "Approved"),
        ("Samantha", "Reed", "Sick", -22, -21, "Migraine.", "Approved"),
        ("Samantha", "Reed", "Casual", 18, 18, "Personal day.", "Pending"),
        ("Tariq", "Mansoor", "Unpaid", -30, -26, "Visa appointment abroad.", "Approved"),
        ("Jessica", "Gomez", "Casual", -5, -5, "Child's school event.", "Approved"),
    ]
    out = []
    reasons_reject = {"Rejected": "Overlaps with quarterly close; please reschedule."}
    for i, (first, last, typ, s, e, reason, status) in enumerate(rows):
        emp = _find(first, last)
        out.append({
            "id": 1092 - i,
            "employee_id": emp["id"],
            "type": typ,
            "start_date": (TODAY + timedelta(days=s)).isoformat(),
            "end_date": (TODAY + timedelta(days=e)).isoformat(),
            "reason": reason,
            "status": status,
            "review_note": reasons_reject.get(status, ""),
        })
    # every employee marked "On Leave" gets an approved request covering today
    covered = {lv["employee_id"] for lv in out
               if lv["status"] == "Approved" and lv["start_date"] <= TODAY.isoformat() <= lv["end_date"]}
    next_id = min(lv["id"] for lv in out) - 1
    for i, emp in enumerate(e for e in EMPLOYEES if e["status"] == "On Leave" and e["id"] not in covered):
        typ = ["Annual", "Sick", "Annual", "Sick", "Maternity/Paternity"][i % 5]
        out.append({
            "id": next_id, "employee_id": emp["id"], "type": typ,
            "start_date": (TODAY - timedelta(days=1 + i % 3)).isoformat(),
            "end_date": (TODAY + timedelta(days=2 + i % 4)).isoformat(),
            "reason": "Medical certificate submitted." if typ == "Sick" else "Planned leave.",
            "status": "Approved", "review_note": "",
        })
        next_id -= 1
    return out


LEAVE_REQUESTS = _make_leaves()

# ------------------------------------------------------------------- payroll
def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def recent_months(n: int = 3) -> list[str]:
    months, d = [], TODAY.replace(day=1)
    for _ in range(n):
        months.append(month_key(d))
        d = (d - timedelta(days=1)).replace(day=1)
    return months


def _payroll_row(pid: int, emp: dict, month: str, status: str) -> dict:
    base = emp["salary"]
    bonus = _rng.choice([0, 150, 250, 300, 450, 600])
    tax = round(base * 0.11, 2)
    insurance = 85.0 if base < 6000 else 120.0
    pension = round(base * 0.02, 2)
    deductions = round(tax + insurance + pension, 2)
    return {
        "id": pid, "employee_id": emp["id"], "month": month,
        "base_salary": float(base), "bonus": float(bonus),
        "tax": tax, "insurance": insurance, "pension": pension,
        "deductions": deductions, "net_salary": round(base + bonus - deductions, 2),
        "status": status,
    }


def _make_payroll():
    rows, pid = [], 1
    current, *past = recent_months(3)
    for emp in EMPLOYEES:
        r = _rng.random()
        status = "Calculated" if r < 0.6 else ("Paid" if r < 0.85 else "Pending")
        rows.append(_payroll_row(pid, emp, current, status))
        pid += 1
        for m in past:
            rows.append(_payroll_row(pid, emp, m, "Paid"))
            pid += 1
    return rows


PAYROLL = _make_payroll()

# ----------------------------------------------------------------- audit log
AUDIT_LOG = [
    ((TODAY, "09:41"), "hr", "LOGIN", "Successful sign-in from 10.0.0.24"),
    ((TODAY, "09:12"), "admin", "UPDATE", "Changed JWT session expiry to 8 hours"),
    ((TODAY - timedelta(days=1), "17:55"), "hr", "APPROVE", "Leave LV-1088 approved"),
    ((TODAY - timedelta(days=1), "16:02"), "hr", "PAYROLL", "Payroll draft calculated for current cycle"),
    ((TODAY - timedelta(days=2), "11:30"), "admin", "CREATE", "User account created for EMP-148"),
    ((TODAY - timedelta(days=3), "08:47"), "admin", "BACKUP", "SQLite snapshot exported (4.2 MB)"),
]
