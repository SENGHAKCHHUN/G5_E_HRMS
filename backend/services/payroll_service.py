"""Payroll (Module 6): net salary = base + bonus - deductions."""
from datetime import datetime

from sqlalchemy.orm import Session

from ..core.errors import BadRequest, NotFound
from ..core.i18n import N_
from ..core.pagination import ALL, Page
from ..integrations import pdf
from ..models import Payroll, User
from ..repositories import audit_repo, employee_repo, payroll_repo
from ..repositories.paging import paginate
from ..serializers import payroll_out
from .access import ensure_self_or_staff, scope_employee
from .settings_service import get_settings, send_mail

# payroll statuses are translated when they appear in documents (e.g. the payslip header)
STATUS_NAMES = [N_("Pending"), N_("Calculated"), N_("Paid")]


def _check_month(month: str):
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise BadRequest("month must be YYYY-MM")


def calculate(line: Payroll, base: float, settings: dict) -> None:
    """Fill the money fields of a payroll line from the base salary and current rates."""
    line.base_salary = float(base)
    line.tax = round(base * float(settings["tax_rate"]) / 100, 2)
    line.pension = round(base * float(settings["pension_rate"]) / 100, 2)
    line.insurance = 85.0 if base < 6000 else 120.0
    line.deductions = round(line.tax + line.pension + line.insurance, 2)
    line.net_salary = round(line.base_salary + (line.bonus or 0) - line.deductions, 2)


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
    """Create missing lines and (re)calculate pending ones for the month."""
    _check_month(month)
    settings = get_settings(db)
    existing = payroll_repo.by_employee_for_month(db, month)
    created = recalculated = 0
    for emp in employee_repo.list_all(db):
        line = existing.get(emp.id)
        if line is None:
            line = payroll_repo.add(db, Payroll(employee_id=emp.id, month=month, bonus=0.0))
            created += 1
        elif line.status != "Pending":
            continue
        else:
            recalculated += 1
        calculate(line, emp.salary, settings)
        line.status = "Calculated"
    audit_repo.add(db, actor.username, "PAYROLL", f"Payroll {month}: {created} created, {recalculated} calculated")
    db.commit()
    return {"month": month, "created": created, "calculated": recalculated}


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
