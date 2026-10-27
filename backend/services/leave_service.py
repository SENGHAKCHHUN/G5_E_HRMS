"""Leave management (Module 5)."""
from collections.abc import Callable
from datetime import date
from functools import partial

from sqlalchemy.orm import Session

from ..core.clock import working_days
from ..core.database import SessionLocal
from ..core.errors import BadRequest, Conflict, Forbidden, NotFound
from ..core.i18n import N_
from ..core.pagination import ALL, Page
from ..integrations import mailer
from ..models import LeaveRequest, User
from ..repositories import audit_repo, employee_repo, leave_repo
from ..repositories.paging import paginate
from ..serializers import leave_out
from .access import ensure_self_or_staff, scope_employee
from .settings_service import get_settings

ALLOWANCE = {"Annual": 20, "Sick": 10, "Casual": 5}
# translated when they appear inside messages (e.g. "Only 3 Annual day(s) remaining")
LEAVE_TYPE_NAMES = [N_("Annual"), N_("Sick"), N_("Casual"), N_("Maternity/Paternity"), N_("Unpaid")]
ALREADY_REVIEWED = {"Approved": N_("This request is already approved"),
                    "Rejected": N_("This request is already rejected"),
                    "other": N_("This request was already reviewed")}


def balance_for(db: Session, employee_id: int) -> dict:
    """Allowances are in working days: weekends (days outside the work week) are not used up."""
    year = date.today().year
    work_week = get_settings(db)["work_week"]
    out = {}
    for leave_type, allowance in ALLOWANCE.items():
        used = sum(len(working_days(lv.start_date, lv.end_date, work_week))
                   for lv in leave_repo.approved_of_type(db, employee_id, leave_type) if lv.start_date.year == year)
        out[leave_type] = {"allowance": allowance, "used": used, "remaining": max(0, allowance - used)}
    return out


def list_for(db: Session, user: User, employee_id: int | None, page: Page = ALL,
             status: str | None = None) -> tuple[list[dict], int]:
    """Staff see all requests; employees only their own."""
    rows, total = paginate(db, leave_repo.requests_query(scope_employee(user, employee_id), status), page)
    work_week = get_settings(db)["work_week"]
    return [leave_out(lv, work_week) for lv in rows], total


def balance(db: Session, user: User, employee_id: int | None) -> dict:
    employee_id = employee_id or user.employee_id
    ensure_self_or_staff(user, employee_id)
    return balance_for(db, employee_id)


def submit(db: Session, user: User, employee_id: int | None, leave_type: str, start: date, end: date,
           reason: str) -> dict:
    employee_id = employee_id or user.employee_id
    ensure_self_or_staff(user, employee_id)
    if employee_id is None or employee_repo.get(db, employee_id) is None:
        raise BadRequest("Unknown employee")
    work_week = get_settings(db)["work_week"]
    days = len(working_days(start, end, work_week))
    if days == 0:
        raise BadRequest("The selected dates contain no working days")
    bal = balance_for(db, employee_id).get(leave_type)
    if bal and days > bal["remaining"]:
        raise BadRequest("Only {remaining} {leave_type} day(s) remaining", remaining=bal["remaining"],
                         leave_type=leave_type)
    overlap = leave_repo.first_overlapping(db, employee_id, start, end)
    if overlap:
        raise Conflict("Overlaps with existing request LV-{id}", id=overlap.id)
    lv = leave_repo.add(db, LeaveRequest(employee_id=employee_id, type=leave_type, start_date=start,
                                         end_date=end, reason=reason))
    db.commit()
    db.refresh(lv)
    return leave_out(lv, work_week)


def send_decision_email(settings: dict, to: str, name: str, lv: dict, reviewer: str) -> None:
    """Tell the employee about the decision. Runs after the response; failures go to the audit log."""
    subject = f"Leave request LV-{lv['id']} {lv['status'].lower()}"
    note = f"\nNote: {lv['review_note']}\n" if lv["review_note"] else ""
    body = (f"Hello {name},\n\nYour {lv['type'].lower()} leave request LV-{lv['id']} "
            f"({lv['start_date']} to {lv['end_date']}, {lv['days']} day(s)) was {lv['status'].lower()} "
            f"by {reviewer}.\n{note}\n{settings['company_name']} HR")
    try:
        mailer.send(settings, to, subject, body)
    except Exception as exc:  # noqa: BLE001 - never fail the decision because of email
        with SessionLocal() as db:
            audit_repo.add(db, "system", "EMAIL_FAIL", f"{subject} -> {to}: {exc}")
            db.commit()


def review(db: Session, reviewer: User, leave_id: int, status: str, note: str) -> tuple[dict, Callable | None]:
    """Approve or reject. Returns the updated request and, if email is set up, a job that sends the
    notification (the caller decides when to run it, e.g. after the HTTP response)."""
    if status == "Rejected" and not note.strip():
        raise BadRequest("Please provide a reason for the rejection")
    lv = leave_repo.get(db, leave_id)
    if lv is None:
        raise NotFound("Leave request not found")
    if lv.employee_id == reviewer.employee_id:
        raise Forbidden("You cannot review your own leave request")
    if lv.status != "Pending":
        raise Conflict(ALREADY_REVIEWED.get(lv.status, ALREADY_REVIEWED["other"]))
    lv.status, lv.review_note = status, note
    audit_repo.add(db, reviewer.username, "APPROVE" if status == "Approved" else "REJECT",
                   f"Leave LV-{lv.id} {status.lower()}")
    db.commit()
    db.refresh(lv)
    settings = get_settings(db)
    out = leave_out(lv, settings["work_week"])
    if not (settings["email_notifications"] and mailer.is_configured(settings)):
        return out, None
    job = partial(send_decision_email, settings, lv.employee.email, lv.employee.first_name, dict(out),
                  reviewer.username)
    out["email_queued"] = True
    return out, job
