"""Fill an empty database with the demo data from seed_data.py.

Runs automatically on first start. To start over, stop the server, delete
hr_system.db and start it again. Last month's payroll is calculated with the real
payroll rules (attendance, leave, tax) and marked paid; this month is left for HR.
"""
from datetime import date, datetime, time

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from .core.security import hash_password
from .models import Attendance, AuditLog, Department, Employee, LeaveRequest, Position, User


def _time(value: str | None) -> time | None:
    return datetime.strptime(value, "%H:%M:%S").time() if value else None


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(User).limit(1)) is not None:
        return False
    from . import seed_data as m  # generated on import, so only load it when needed

    dept_cols = {c.key for c in Department.__table__.columns}
    for d in m.DEPARTMENTS:
        db.add(Department(**{k: v for k, v in d.items() if k in dept_cols}))
    db.flush()
    for p in m.POSITIONS:
        db.add(Position(**p))
    db.flush()

    emp_cols = {c.key for c in Employee.__table__.columns}
    for e in m.EMPLOYEES:
        fields = {k: v for k, v in e.items() if k in emp_cols}
        fields["hire_date"] = date.fromisoformat(e["hire_date"])
        db.add(Employee(**fields))
    db.flush()

    for u in m.USERS:
        db.add(User(id=u["id"], username=u["username"], password_hash=hash_password(u["password"]),
                    role=u["role"], employee_id=u["employee_id"]))
    db.flush()

    db.execute(insert(Attendance), [{
        "employee_id": a["employee_id"], "date": date.fromisoformat(a["date"]),
        "check_in": _time(a["check_in"]), "check_out": _time(a["check_out"]),
        "status": a["status"], "source": "seed", "ip_address": "",
    } for a in m.ATTENDANCE])

    for lv in m.LEAVE_REQUESTS:
        db.add(LeaveRequest(id=lv["id"], employee_id=lv["employee_id"], type=lv["type"],
                            start_date=date.fromisoformat(lv["start_date"]),
                            end_date=date.fromisoformat(lv["end_date"]), reason=lv["reason"],
                            status=lv["status"], review_note=lv["review_note"]))

    for (day, hhmm), user, action, detail in m.AUDIT_LOG:
        db.add(AuditLog(timestamp=datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time()),
                        username=user, action=action, detail=detail))
    db.commit()

    from .services import payroll_service
    admin = db.get(User, 1)
    last_month = m.FIRST_DAY.strftime("%Y-%m")
    payroll_service.generate(db, admin, last_month)
    payroll_service.pay(db, admin, last_month)
    return True
