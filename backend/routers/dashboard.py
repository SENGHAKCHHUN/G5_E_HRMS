"""Dashboard endpoints (Module 7)."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.security import STAFF
from ..dependencies import get_current_user, get_db, require_roles
from ..models import User
from ..schemas import AttendanceOut, DashboardStats
from ..services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(_: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return dashboard_service.stats(db)


@router.get("/summary.pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def summary_pdf(user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """The dashboard overview as a printable PDF."""
    return Response(dashboard_service.summary_pdf(db, user), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="dashboard_summary.pdf"'})


@router.get("/checkins", response_model=list[AttendanceOut])
def recent_checkins(limit: int = 5, _: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return dashboard_service.recent_checkins(db, limit)


@router.get("/notifications", response_model=list[str])
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Short alerts for the bell menu, based on live data."""
    return dashboard_service.notifications(db, user)
