"""Login accounts managed by an Admin: list, password reset ('forgot password'), 2FA reset."""
from sqlalchemy.orm import Session

from ..core import security
from ..core.errors import NotFound
from ..models import User
from ..repositories import audit_repo, login_attempt_repo, user_repo


def _get(db: Session, user_id: int) -> User:
    user = user_repo.get(db, user_id)
    if user is None:
        raise NotFound("User not found")
    return user


def list_users(db: Session) -> list[dict]:
    return [{"id": u.id, "username": u.username, "role": u.role, "employee_id": u.employee_id,
             "employee": f"{u.employee.full_name} ({u.employee.code})" if u.employee else "-",
             "totp_enabled": u.totp_enabled, "must_change_password": u.must_change_password}
            for u in user_repo.list_all(db)]


def reset_password(db: Session, admin: User, user_id: int) -> dict:
    """Issue a one-time temporary password; the user must change it at next login."""
    user = _get(db, user_id)
    temp = security.temporary_password()
    user.password_hash = security.hash_password(temp)
    user.must_change_password = True
    login_attempt_repo.clear(db, user.username)  # also lifts a lockout after failed logins
    audit_repo.add(db, admin.username, "PASSWORD", f"Password reset for '{user.username}'")
    db.commit()
    return {"username": user.username, "temporary_password": temp}


def reset_2fa(db: Session, admin: User, user_id: int) -> dict:
    """For a user who lost their phone: turns 2FA off so they can sign in and set it up again."""
    user = _get(db, user_id)
    user.totp_enabled = False
    user.totp_secret = None
    audit_repo.add(db, admin.username, "2FA", f"Two-factor authentication reset for '{user.username}'")
    db.commit()
    return {"username": user.username, "totp_enabled": False}
