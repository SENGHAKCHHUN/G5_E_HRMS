"""Login, sessions, password changes and two-factor authentication."""
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from ..core import security, totp
from ..core.config import config
from ..core.errors import BadRequest, Conflict, Forbidden, TooManyRequests, Unauthorized
from ..core.i18n import N_
from ..core.logging import get_logger
from ..models import User
from ..repositories import audit_repo, login_attempt_repo, user_repo
from .settings_service import get_settings

log = get_logger("auth")

# Until these are resolved the user may only use the account endpoints (/auth/*)
PASSWORD_CHANGE_REQUIRED = "password_change_required"
MFA_SETUP_REQUIRED = "mfa_setup_required"
OTP_REQUIRED = "otp_required"
SESSION_EXPIRED = N_("Session expired, please sign in again")


def mfa_required(user: User, settings: dict) -> bool:
    return bool(settings.get("enforce_mfa")) and user.role in security.STAFF


def pending_action(user: User, settings: dict) -> str | None:
    if user.must_change_password:
        return PASSWORD_CHANGE_REQUIRED
    if mfa_required(user, settings) and not user.totp_enabled:
        return MFA_SETUP_REQUIRED
    return None


def session_payload(user: User, settings: dict) -> dict:
    emp = user.employee
    return {
        "user_id": user.id, "username": user.username, "role": user.role,
        "employee_id": emp.id if emp else None,
        "name": emp.full_name if emp else user.username,
        "initials": (emp.first_name[0] + emp.last_name[0]) if emp else user.username[:2].upper(),
        "department_id": emp.department_id if emp else None,
        "department": emp.department.name if emp else "-",
        "position": emp.position if emp else user.role,
        "totp_enabled": user.totp_enabled,
        "mfa_required": mfa_required(user, settings),
        "pending_action": pending_action(user, settings),
    }


def _token_response(db: Session, user: User) -> dict:
    settings = get_settings(db)
    token = security.create_access_token(user.id, user.role, user.password_hash, int(settings["jwt_hours"]))
    return {"access_token": token, "token_type": "bearer", "user": session_payload(user, settings)}


def user_from_token(db: Session, token: str, account_endpoint: bool) -> User:
    """Resolve the signed-in user. Outside the account endpoints, pending actions block access."""
    payload = security.decode_access_token(token)
    if payload is None:
        raise Unauthorized(SESSION_EXPIRED)
    user = user_repo.get(db, int(payload["sub"]))
    if user is None or payload.get("pw") != security.password_stamp(user.password_hash):
        raise Unauthorized(SESSION_EXPIRED)
    if not account_endpoint:
        action = pending_action(user, get_settings(db))
        if action:
            raise Forbidden(action)
    return user


def _ensure_not_locked(db: Session, name: str):
    """After too many recent failures the account is locked for a while (stops password guessing)."""
    window = timedelta(minutes=config.login_lockout_minutes)
    failures, latest = login_attempt_repo.failures_since(db, name, datetime.now() - window)
    if failures >= config.login_max_failures:
        minutes = max(1, ceil(((latest + window) - datetime.now()).total_seconds() / 60))
        raise TooManyRequests("Too many failed sign-in attempts. Try again in {minutes} minute(s) "
                              "or ask an Admin to reset your password.", minutes=minutes)


def _record_failure(db: Session, name: str, ip: str, reason: str):
    login_attempt_repo.add_failure(db, name, ip)
    audit_repo.add(db, name[:60], "LOGIN_FAIL", f"{reason} from {ip}")
    db.commit()
    log.warning("Failed sign-in for '%s' from %s (%s)", name, ip, reason)


def login(db: Session, username: str, password: str, otp: str | None, ip: str) -> dict:
    name = username.strip().lower()
    _ensure_not_locked(db, name)
    user = user_repo.get_by_username(db, name) or user_repo.get_by_employee_email(db, name)
    valid, upgraded_hash = security.verify_and_update(password, user.password_hash) if user else (False, None)
    if not valid:
        _record_failure(db, name, ip, "Wrong username or password")
        raise Unauthorized("Invalid username or password")
    if user.totp_enabled:
        if not otp:
            raise Unauthorized(OTP_REQUIRED)
        if not totp.verify(user.totp_secret, otp):
            _record_failure(db, name, ip, "Wrong 2FA code")
            raise Unauthorized("Invalid authentication code")
    if upgraded_hash:  # stored with an older algorithm (bcrypt): re-hash with Argon2
        user.password_hash = upgraded_hash
    login_attempt_repo.clear(db, name)
    audit_repo.add(db, user.username, "LOGIN", f"Successful sign-in from {ip}")
    db.commit()
    return _token_response(db, user)


def me(db: Session, user: User) -> dict:
    return session_payload(user, get_settings(db))


def change_password(db: Session, user: User, current_password: str, new_password: str) -> dict:
    """Returns a fresh token: tokens issued before the change stop working."""
    if not security.verify_password(current_password, user.password_hash):
        raise BadRequest("Your current password is incorrect")
    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    audit_repo.add(db, user.username, "PASSWORD", "Changed own password")
    db.commit()
    return _token_response(db, user)


def setup_2fa(db: Session, user: User) -> dict:
    if user.totp_enabled:
        raise Conflict("Two-factor authentication is already on")
    user.totp_secret = totp.new_secret()
    db.commit()
    return {"secret": user.totp_secret, "uri": totp.provisioning_uri(user.totp_secret, user.username)}


def enable_2fa(db: Session, user: User, code: str) -> dict:
    if not user.totp_secret:
        raise BadRequest("Start the setup first")
    if not totp.verify(user.totp_secret, code):
        raise BadRequest("That code is not valid. Check the time on your phone and try the newest code.")
    user.totp_enabled = True
    audit_repo.add(db, user.username, "2FA", "Two-factor authentication enabled")
    db.commit()
    return me(db, user)


def disable_2fa(db: Session, user: User, password: str) -> dict:
    settings = get_settings(db)
    if mfa_required(user, settings):
        raise Forbidden("Two-factor authentication is required for your role")
    if not security.verify_password(password, user.password_hash):
        raise BadRequest("Your password is incorrect")
    user.totp_enabled = False
    user.totp_secret = None
    audit_repo.add(db, user.username, "2FA", "Two-factor authentication disabled")
    db.commit()
    return session_payload(user, settings)
