"""Payroll endpoints (Module 6)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..core.pagination import Page
from ..core.security import STAFF
from ..dependencies import get_current_user, get_db, paged, pagination, require_roles
from ..models import User
from ..schemas import EmailSent, PayrollOut, PayrollPaid, PayrollRun, PayrollSummary
from ..services import payroll_service

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.get("", response_model=list[PayrollOut])
def list_payroll(response: Response, month: str | None = None, employee_id: int | None = None,
                 status: str | None = None, search: str | None = None, department_id: int | None = None,
                 page: Page = Depends(pagination), user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Staff see everyone; employees only their own payslips. Total count in X-Total-Count."""
    return paged(response, payroll_service.list_for(db, user, month, employee_id, page, status, search,
                                                    department_id))


@router.get("/summary", response_model=PayrollSummary)
def payroll_summary(month: str | None = None, employee_id: int | None = None,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Gross, tax and net totals and lines per status (employees: their own)."""
    return payroll_service.summary(db, user, month, employee_id)


@router.post("/generate", response_model=PayrollRun)
def generate_payroll(month: str, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Create missing lines and (re)calculate pending ones for the month."""
    return payroll_service.generate(db, user, month)


@router.post("/pay", response_model=PayrollPaid)
def pay_payroll(month: str, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Mark every calculated line for the month as paid (disbursed)."""
    return payroll_service.pay(db, user, month)


@router.get("/{payroll_id}/pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def payslip_pdf(payroll_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Printable payslip. Employees can only download their own."""
    filename, data = payroll_service.payslip_pdf(db, user, payroll_id)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/{payroll_id}/email", response_model=EmailSent)
def email_payslip(payroll_id: int, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Email the payslip PDF to the employee's work address."""
    return payroll_service.email_payslip(db, user, payroll_id)
