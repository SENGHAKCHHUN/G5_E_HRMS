"""User account endpoints (Admin): list accounts, reset password, reset 2FA."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.security import ADMIN
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import TemporaryPassword, TwoFactorReset, UserAccount
from ..services import user_service

router = APIRouter(prefix="/users", tags=["User Accounts"])


@router.get("", response_model=list[UserAccount])
def list_users(_: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    return user_service.list_users(db)


@router.post("/{user_id}/reset-password", response_model=TemporaryPassword)
def reset_password(user_id: int, admin: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    """'Forgot password': issue a one-time temporary password; the user must change it at next login."""
    return user_service.reset_password(db, admin, user_id)


@router.post("/{user_id}/reset-2fa", response_model=TwoFactorReset)
def reset_2fa(user_id: int, admin: User = Depends(require_roles(ADMIN)), db: Session = Depends(get_db)):
    """For a user who lost their phone: turns 2FA off so they can sign in and set it up again."""
    return user_service.reset_2fa(db, admin, user_id)
