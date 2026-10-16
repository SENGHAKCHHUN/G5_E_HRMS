"""Attendance endpoints (Module 4). The check-in rules live in services/attendance_service.py."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..core.pagination import Page
from ..core.security import STAFF
from ..dependencies import client_ip, get_current_user, get_db, paged, pagination, require_roles
from ..models import User
from ..schemas import AttendanceOut, AttendanceSummary, ManualAttendance, PunchPolicy
from ..services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/policy", response_model=PunchPolicy)
def punch_policy(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lets the app show whether this device may punch right now."""
    return attendance_service.get_policy(db, user, client_ip(request))


@router.get("/today", response_model=AttendanceOut | None)
def today_record(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The signed-in user's record for today (or null)."""
    return attendance_service.today_record(db, user)


@router.post("/check-in", response_model=AttendanceOut)
def check_in(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record check-in for the signed-in user, using the server's clock."""
    return attendance_service.check_in(db, user, client_ip(request))


@router.post("/check-out", response_model=AttendanceOut)
def check_out(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record check-out for the signed-in user, using the server's clock."""
    return attendance_service.check_out(db, user, client_ip(request))


@router.get("", response_model=list[AttendanceOut])
def list_attendance(response: Response, employee_id: int | None = None, month: str | None = None,
                    status: str | None = None, search: str | None = None, department_id: int | None = None,
                    page: Page = Depends(pagination), user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Attendance records. month = 'YYYY-MM'. Employees always get only their own.
    Total count in X-Total-Count."""
    return paged(response, attendance_service.list_for(db, user, employee_id, month, page, status, search,
                                                       department_id))


@router.get("/summary", response_model=AttendanceSummary)
def attendance_summary(employee_id: int | None = None, month: str | None = None,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Punctuality counts and average hours for a month (employees: their own)."""
    return attendance_service.summary(db, user, employee_id, month)


@router.post("", status_code=201, response_model=AttendanceOut)
def manual_entry(data: ManualAttendance, user: User = Depends(require_roles(*STAFF)),
                 db: Session = Depends(get_db)):
    """HR/Admin: record or correct a day's punches (replaces that day's record)."""
    return attendance_service.manual_entry(db, user, data.employee_id, data.date, data.check_in,
                                           data.check_out, data.status)
