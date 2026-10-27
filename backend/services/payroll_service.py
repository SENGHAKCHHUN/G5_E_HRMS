"""Payroll (Module 6).

gross = base salary + overtime + bonus + adjustment
net   = gross - (unpaid days + income tax + pension + health insurance)

Rules:
  1. Only people employed in the month are paid: hired on or before its last day, and not
     terminated before its first day. Terminated without a last working day = not paid.
  2. A joining or leaving month pays base salary x days employed / days in the month.
  3. Calculating again recalculates every line that is not Paid (new salary, rates and days),
     keeps its bonus, adjustment and note, and removes lines of people no longer eligible.
  4. Paid lines never change.
  5. deduct_unpaid: each Absent day and approved Unpaid leave day on a working day deducts one
     daily rate (salary / working days of the month); a Half Day deducts half of one.
  6. Overtime (time after overtime_after, never on a Half Day) is paid at
     hourly rate (daily rate / shift hours) x overtime_rate.
  7. Income tax: a flat tax_rate, or tax_brackets (progressive). With tax_bonus, bonus and
     overtime are taxed too. Pension is taken from the base salary earned (after unpaid days).
  8. Health insurance: insurance_amount, or insurance_high_amount from insurance_threshold up.
"""
import calendar
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from ..core.clock import working_days
from ..core.errors import BadRequest, NotFound
from ..core.i18n import N_
from ..core.pagination import ALL, Page
from ..integrations import pdf
from ..models import Employee, Payroll, User
from ..repositories import attendance_repo, audit_repo, employee_repo, leave_repo, payroll_repo
from ..repositories.paging import paginate
from ..serializers import payroll_out
from .access import ensure_self_or_staff, scope_employee
from .settings_service import get_settings, parse_brackets, send_mail

# payroll statuses are translated when they appear in documents (e.g. the payslip header)
STATUS_NAMES = [N_("Pending"), N_("Calculated"), N_("Paid")]


def _check_month(month: str):
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise BadRequest("month must be YYYY-MM")


def income_tax(taxable: float, settings: dict) -> float:
    """Flat tax_rate, or progressive tax_brackets: each rate applies to the part of pay above its amount."""
    taxable = max(0.0, taxable)
    if not settings.get("tax_brackets"):
        return round(taxable * float(settings["tax_rate"]) / 100, 2)
    brackets = parse_brackets(settings["tax_brackets"])
    tax = 0.0
    for i, (start, rate) in enumerate(brackets):
        end = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if taxable > start:
            tax += (min(taxable, end) - start) * rate / 100
    return round(tax, 2)


def calculate(line: Payroll, base: float, settings: dict) -> None:
    """Fill the money fields of a payroll line from its base salary, attendance figures and the rates."""
    line.base_salary = float(base)
    unpaid = min(getattr(line, "unpaid_deduction", 0) or 0, line.base_salary)
    overtime = getattr(line, "overtime_pay", 0) or 0
    earned = line.base_salary - unpaid
    taxable = earned + ((line.bonus or 0) + overtime if settings["tax_bonus"] else 0)
    line.tax = income_tax(taxable, settings)
    line.pension = round(earned * float(settings["pension_rate"]) / 100, 2)
    high = line.base_salary >= float(settings["insurance_threshold"])
    line.insurance = float(settings["insurance_high_amount"] if high else settings["insurance_amount"])
    line.deductions = round(unpaid + line.tax + line.pension + line.insurance, 2)
    line.net_salary = round(line.base_salary + overtime + (line.bonus or 0) + (getattr(line, "adjustment", 0) or 0)
                            - line.deductions, 2)


def _hm(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def overtime_hours(rec, settings: dict) -> float:
    """Hours after overtime_after (a check-out earlier than the check-in was after midnight)."""
    if rec.check_in is None or rec.check_out is None or rec.status == "Half Day":
        return 0.0
    start = datetime.combine(rec.date, rec.check_in)
    end = datetime.combine(rec.date, rec.check_out)
    if end < start:
        end += timedelta(days=1)
    from_ = max(start, datetime.combine(rec.date, _hm(settings["overtime_after"])))
    return max(0.0, (end - from_).total_seconds() / 3600)


def attendance_pay(emp: Employee, month: str, records: list, unpaid_leaves: list, settings: dict) -> dict:
    """Unpaid days and overtime of one employee in the month (rules 5, 6), with their amounts."""
    year, mon = int(month[:4]), int(month[5:7])
    first, last = date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])
    start = max(first, emp.hire_date)
    end = min(last, emp.termination_date) if emp.termination_date else last
    work_days = set(working_days(start, end, settings["work_week"]))
    unpaid: dict[date, float] = {}
    for rec in records:
        if rec.date in work_days and rec.status in ("Absent", "Half Day"):
            unpaid[rec.date] = 1.0 if rec.status == "Absent" else 0.5
    for lv in unpaid_leaves:
        for day in working_days(max(lv.start_date, start), min(lv.end_date, end), settings["work_week"]):
            unpaid[day] = 1.0
    hours = round(sum(overtime_hours(r, settings) for r in records if start <= r.date <= end), 2)

    month_work_days = len(working_days(first, last, settings["work_week"]))
    daily = emp.salary / month_work_days if month_work_days else 0.0
    shift = (datetime.combine(first, _hm(settings["shift_end"]))
             - datetime.combine(first, _hm(settings["shift_start"]))).total_seconds() / 3600
    hourly = daily / shift if shift > 0 else 0.0
    days = sum(unpaid.values()) if settings["deduct_unpaid"] else 0.0
    return {"unpaid_days": days, "unpaid_deduction": round(daily * days, 2), "overtime_hours": hours,
            "overtime_pay": round(hourly * hours * float(settings["overtime_rate"]), 2)}


def employed_days(emp: Employee, month: str) -> tuple[int, int]:
    """(days employed in the month, days in the month). 0 days = not paid this month (rule 1)."""
    year, mon = int(month[:4]), int(month[5:7])
    month_days = calendar.monthrange(year, mon)[1]
    first, last = date(year, mon, 1), date(year, mon, month_days)
    if emp.status == "Terminated" and emp.termination_date is None:
        return 0, month_days
    start = max(first, emp.hire_date)
    end = min(last, emp.termination_date) if emp.termination_date else last
    return max(0, (end - start).days + 1), month_days


def list_for(db: Session, user: User, month: str | None, employee_id: int | None, page: Page = ALL,
             status: str | None = None, search: str | None = None,
             department_id: int | None = None) -> tuple[list[dict], int]:
    """Staff see everyone; employees only their own payslips."""
    if month:
        _check_month(month)
    stmt = payroll_repo.lines_query(month, scope_employee(user, employee_id), status, search, department_id)
    rows, total = paginate(db, stmt, page)
    return [payroll_out(p) for p in rows], total


def summary(db: Session, user: User, month: str | None, employee_id: int | None) -> dict:
    """Totals for the payroll cards (gross, tax, net, lines per status)."""
    if month:
        _check_month(month)
    return payroll_repo.totals(db, month, scope_employee(user, employee_id))


def generate(db: Session, actor: User, month: str) -> dict:
    """Create missing lines and recalculate every unpaid one for the month (rules 1-4)."""
    _check_month(month)
    settings = get_settings(db)
    existing = payroll_repo.by_employee_for_month(db, month)
    year, mon = int(month[:4]), int(month[5:7])
    first, last = date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])
    records: dict[int, list] = {}
    for rec in attendance_repo.between(db, first, last):
        records.setdefault(rec.employee_id, []).append(rec)
    leaves: dict[int, list] = {}
    for lv in leave_repo.approved_between(db, first, last, "Unpaid"):
        leaves.setdefault(lv.employee_id, []).append(lv)
    created = recalculated = removed = 0
    for emp in employee_repo.list_all(db):
        line = existing.get(emp.id)
        if line is not None and line.status == "Paid":
            continue
        days, month_days = employed_days(emp, month)
        if days == 0:
            if line is not None:  # e.g. terminated or hire date moved since the last calculation
                payroll_repo.delete(db, line)
                removed += 1
            continue
        if line is None:
            line = payroll_repo.add(db, Payroll(employee_id=emp.id, month=month, bonus=0.0, adjustment=0.0,
                                                note=""))
            created += 1
        else:
            recalculated += 1
        line.paid_days = days if days < month_days else None
        for key, value in attendance_pay(emp, month, records.get(emp.id, []), leaves.get(emp.id, []),
                                         settings).items():
            setattr(line, key, value)
        calculate(line, round(emp.salary * days / month_days, 2), settings)
        line.status = "Calculated"
    audit_repo.add(db, actor.username, "PAYROLL",
                   f"Payroll {month}: {created} created, {recalculated} recalculated, {removed} removed")
    db.commit()
    return {"month": month, "created": created, "calculated": recalculated, "removed": removed}


def update_line(db: Session, actor: User, payroll_id: int, changes: dict) -> dict:
    """Set a line's bonus, adjustment or note before it is paid; net pay follows."""
    line = _get(db, payroll_id)
    if line.status == "Paid":
        raise BadRequest("A paid payroll line cannot be changed")
    for key in ("bonus", "adjustment", "note"):
        if key in changes:
            setattr(line, key, changes[key])
    calculate(line, line.base_salary, get_settings(db))  # a taxed bonus changes the tax too
    audit_repo.add(db, actor.username, "PAYROLL",
                   f"Payroll {line.employee.code} {line.month}: bonus {line.bonus:g}, adjustment {line.adjustment:g}")
    db.commit()
    db.refresh(line)
    return payroll_out(line)


def pay(db: Session, actor: User, month: str) -> dict:
    """Mark every calculated line for the month as paid (disbursed)."""
    _check_month(month)
    lines = payroll_repo.with_status(db, month, "Calculated")
    for line in lines:
        line.status = "Paid"
    audit_repo.add(db, actor.username, "PAYROLL", f"Payroll {month}: {len(lines)} payslips disbursed")
    db.commit()
    return {"month": month, "paid": len(lines)}


def _get(db: Session, payroll_id: int) -> Payroll:
    line = payroll_repo.get(db, payroll_id)
    if line is None:
        raise NotFound("Payroll line not found")
    return line


def payslip_pdf(db: Session, user: User, payroll_id: int) -> tuple[str, bytes]:
    """Printable payslip (filename, bytes). Employees can only download their own."""
    line = _get(db, payroll_id)
    ensure_self_or_staff(user, line.employee_id)
    data = pdf.payslip_pdf(payroll_out(line), get_settings(db))
    return f"payslip_{line.employee.code}_{line.month}.pdf", data


def email_payslip(db: Session, actor: User, payroll_id: int) -> dict:
    """Email the payslip PDF to the employee's work address."""
    line = _get(db, payroll_id)
    emp = line.employee
    settings = get_settings(db)
    label = pdf.month_label(line.month)
    send_mail(settings, emp.email, f"Your payslip for {label}",
              f"Hello {emp.first_name},\n\nPlease find attached your payslip for {label}.\n"
              f"Net pay: {pdf.money(line.net_salary, settings['currency'])}\n\n{settings['company_name']} HR",
              [(f"payslip_{emp.code}_{line.month}.pdf", pdf.payslip_pdf(payroll_out(line), settings),
                "application/pdf")])
    audit_repo.add(db, actor.username, "EMAIL", f"Payslip {emp.code} {line.month} sent to {emp.email}")
    db.commit()
    return {"sent": True, "to": emp.email}
