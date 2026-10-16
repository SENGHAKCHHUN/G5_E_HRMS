"""Leave endpoints (Module 5)."""
from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.orm import Session

from ..core.pagination import Page
from ..core.security import STAFF
from ..dependencies import get_current_user, get_db, paged, pagination, require_roles
from ..models import User
from ..schemas import LeaveBalanceItem, LeaveIn, LeaveOut, ReviewIn
from ..services import leave_service

router = APIRouter(prefix="/leaves", tags=["Leave"])


@router.get("", response_model=list[LeaveOut])
def list_leaves(response: Response, employee_id: int | None = None, status: str | None = None,
                page: Page = Depends(pagination), user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Staff see all requests; employees only their own. Total count in X-Total-Count."""
    return paged(response, leave_service.list_for(db, user, employee_id, page, status))


@router.get("/balance", response_model=dict[str, LeaveBalanceItem])
def leave_balance(employee_id: int | None = None, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return leave_service.balance(db, user, employee_id)


@router.post("", status_code=201, response_model=LeaveOut)
def submit_leave(data: LeaveIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leave_service.submit(db, user, data.employee_id, data.type, data.start_date, data.end_date, data.reason)


def _review(db: Session, user: User, leave_id: int, status: str, note: str, tasks: BackgroundTasks):
    result, email_job = leave_service.review(db, user, leave_id, status, note)
    if email_job:
        tasks.add_task(email_job)  # sent after the response, so a slow mail server never blocks HR
    return result


@router.put("/{leave_id}/approve", response_model=LeaveOut)
def approve_leave(leave_id: int, tasks: BackgroundTasks, data: ReviewIn | None = None,
                  user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return _review(db, user, leave_id, "Approved", data.note if data else "", tasks)


@router.put("/{leave_id}/reject", response_model=LeaveOut)
def reject_leave(leave_id: int, data: ReviewIn, tasks: BackgroundTasks,
                 user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return _review(db, user, leave_id, "Rejected", data.note, tasks)
