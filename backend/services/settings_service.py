"""System settings, test email, database information and backups."""
import os
import sqlite3
import tempfile
from datetime import datetime

from sqlalchemy.orm import Session

from ..core import crypto, database
from ..core.config import config
from ..core.errors import BadRequest, ExternalServiceError
from ..core.pagination import Page
from ..integrations import mailer
from ..models import User
from ..repositories import attendance_repo, audit_repo, employee_repo, leave_repo, payroll_repo, setting_repo
from ..repositories.paging import paginate

DEFAULTS = {
    "company_name": "HRMS Technologies Inc.",
    "domain": "hrms.corp",
    "timezone": "(UTC+07:00) Bangkok, Hanoi, Phnom Penh",
    "work_week": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "api_url": "http://127.0.0.1:8000",
    "db_url": "sqlite:///./hr_system.db",
    "jwt_hours": 8,
    "enforce_mfa": False,             # require 2FA for Admin / HR Manager accounts
    # attendance policy
    "shift_start": "09:00",
    "shift_end": "18:00",
    "grace_minutes": 15,
    "overtime_after": "18:00",
    # check-in rules (enforced by the attendance service, using server time)
    "checkin_open": "06:00",
    "checkin_close": "12:00",
    "restrict_network": True,
    # this machine + private LAN ranges = "inside the office" when the server is hosted there
    "office_networks": "127.0.0.1/32, ::1/128, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16",
    "remote_exempt": True,            # work mode "Remote" may punch from anywhere
    # payroll
    "tax_rate": 11.0,
    "pension_rate": 2.0,
    "pay_day": 28,
    "currency": "USD",
    # email (SMTP) for payslips and leave notifications
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "smtp_tls": True,
    "email_notifications": True,
}

SECRET_KEYS = {"smtp_password"}  # never sent back to the app


def get_settings(db: Session) -> dict:
    """All settings with secrets decrypted (for internal use - never return this over the API)."""
    values = dict(DEFAULTS)
    values.update(setting_repo.load_all(db))
    values["smtp_password"] = config.smtp_password or crypto.decrypt(values.get("smtp_password", ""))
    return values


def public_settings(values: dict) -> dict:
    """Settings safe to return over the API (secrets replaced by a 'set' flag)."""
    out = {k: v for k, v in values.items() if k not in SECRET_KEYS}
    out["smtp_password_set"] = bool(values.get("smtp_password"))
    return out


def read_public(db: Session) -> dict:
    return public_settings(get_settings(db))


def update(db: Session, actor: User, changes: dict) -> dict:
    if not changes.get("smtp_password"):
        changes.pop("smtp_password", None)  # blank = keep the stored password
    if changes.get("enforce_mfa") and not actor.totp_enabled:
        # otherwise the admin would immediately lock themselves out of everything but 2FA setup
        raise BadRequest("Turn on two-factor authentication for your own account first "
                         "(user menu > Two-Factor Authentication).")
    current = get_settings(db)
    if changes.get("checkin_open", current["checkin_open"]) >= changes.get("checkin_close", current["checkin_close"]):
        raise BadRequest("Check-in must open before it closes")
    for key, value in changes.items():
        if key in SECRET_KEYS:
            value = crypto.encrypt(value)  # stored encrypted, never in plain text
        if key in DEFAULTS:
            setting_repo.save(db, key, value)
    audit_repo.add(db, actor.username, "SETTINGS",
                   "Updated: " + ", ".join(sorted(changes)) if changes else "No changes")
    db.commit()
    return read_public(db)


def send_mail(settings: dict, to: str, subject: str, body: str,
              attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    """Send an email, translating mail failures into domain errors."""
    try:
        mailer.send(settings, to, subject, body, attachments)
    except mailer.EmailNotConfigured as exc:
        raise BadRequest(str(exc))
    except Exception as exc:  # noqa: BLE001 - any SMTP/network failure is reported to the user
        raise ExternalServiceError("Sending failed: {error}", error=str(exc))


def send_test_email(db: Session, actor: User, to: str) -> dict:
    settings = get_settings(db)
    send_mail(settings, to, f"{settings['company_name']} HRMS test email",
              "This is a test message from the HRMS. Email delivery is working.")
    audit_repo.add(db, actor.username, "EMAIL", f"Test email sent to {to}")
    db.commit()
    return {"sent": True}


def database_info(db: Session) -> dict:
    url = database.DATABASE_URL
    size_mb = None
    if database.is_sqlite():
        path = database.sqlite_path()
        size_mb = round(os.path.getsize(path) / 1e6, 2) if os.path.exists(path) else 0
    return {
        "driver": db.get_bind().dialect.name,
        "url": url.split("@")[-1] if "@" in url else url,  # hide credentials
        "size_mb": size_mb,
        "employees": employee_repo.count(db),
        "attendance_rows": attendance_repo.count(db),
        "leave_requests": leave_repo.count(db),
        "payroll_rows": payroll_repo.count(db),
    }


def backup_database(db: Session, actor: User) -> tuple[str, bytes]:
    """A consistent copy of the SQLite database (safe while the server is running)."""
    if not database.is_sqlite():
        raise BadRequest("Built-in backup only supports SQLite. Use your database's own tools "
                         "(e.g. pg_dump or mysqldump).")
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = sqlite3.connect(database.sqlite_path())
        dst = sqlite3.connect(tmp)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        os.remove(tmp)
    audit_repo.add(db, actor.username, "BACKUP", f"Database backup downloaded ({len(data) / 1e6:.1f} MB)")
    db.commit()
    return f"hrms_backup_{datetime.now():%Y%m%d_%H%M}.db", data


def audit_log(db: Session, page: Page) -> tuple[list[dict], int]:
    rows, total = paginate(db, audit_repo.recent_query(), page)
    return [{"when": r.timestamp.strftime("%Y-%m-%d %H:%M"), "user": r.username, "action": r.action,
             "detail": r.detail} for r in rows], total
