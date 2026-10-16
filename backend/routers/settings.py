"""Settings endpoints: system settings, email test, database info/backup, audit log (Admin)."""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..core.pagination import Page
from ..core.security import ADMIN
from ..dependencies import get_current_user, get_db, paged, require_roles
from ..models import User
from ..schemas import AuditEntry, DatabaseInfo, EmailSent, SettingsIn, SettingsOut, TestEmailIn
from ..services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsOut)
def read_settings(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Readable by everyone signed in (payslips need the company name, attendance the shift).
    The SMTP password is never returned."""
    return settings_service.read_public(db)


@router.put("", response_model=SettingsOut)
def update_settings(data: SettingsIn, user: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    return settings_service.update(db, user, data.model_dump(exclude_unset=True, exclude_none=True))


@router.post("/test-email", response_model=EmailSent)
def test_email(data: TestEmailIn, user: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    return settings_service.send_test_email(db, user, data.to)


@router.get("/database", response_model=DatabaseInfo)
def database_info(_: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    return settings_service.database_info(db)


@router.get("/backup", response_class=Response,
            responses={200: {"content": {"application/octet-stream": {}}}})
def backup_database(user: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    """Download a consistent copy of the SQLite database (safe while the server is running)."""
    filename, data = settings_service.backup_database(db, user)
    return Response(data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/audit", response_model=list[AuditEntry])
def audit_log(response: Response, limit: int = Query(50, ge=1, le=1000), offset: int = Query(0, ge=0),
              _: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    """Newest first. Total count in X-Total-Count."""
    return paged(response, settings_service.audit_log(db, Page(limit=limit, offset=offset)))
