"""Authentication endpoints: login, profile, password change, two-factor authentication."""
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from ..dependencies import client_ip, get_current_user, get_db
from ..models import User
from ..schemas import LoginResponse, OtpCode, PasswordChange, PasswordConfirm, SessionUser, TwoFactorSetup
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(request: Request, username: str = Form(), password: str = Form(), otp: str | None = Form(None),
          db: Session = Depends(get_db)):
    """Log in with username (or work email) + password and receive a JWT token.

    Accounts with two-factor authentication must also send `otp` (6-digit code);
    without it the response is 401 with detail 'otp_required'. After repeated failures
    the account is locked for a while (429).
    """
    return auth_service.login(db, username, password, otp, client_ip(request))


@router.get("/me", response_model=SessionUser)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.me(db, user)


@router.post("/change-password", response_model=LoginResponse)
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change your own password. Returns a fresh token (older tokens stop working)."""
    return auth_service.change_password(db, user, data.current_password, data.new_password)


@router.post("/2fa/setup", response_model=TwoFactorSetup)
def setup_2fa(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start 2FA enrolment: returns a secret to add to an authenticator app."""
    return auth_service.setup_2fa(db, user)


@router.post("/2fa/enable", response_model=SessionUser)
def enable_2fa(data: OtpCode, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Finish enrolment by proving the authenticator app produces valid codes."""
    return auth_service.enable_2fa(db, user, data.code)


@router.post("/2fa/disable", response_model=SessionUser)
def disable_2fa(data: PasswordConfirm, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.disable_2fa(db, user, data.password)
