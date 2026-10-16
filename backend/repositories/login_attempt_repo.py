"""Database access for failed sign-in attempts (login protection)."""
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import LoginAttempt


def add_failure(db: Session, username: str, ip: str) -> None:
    db.add(LoginAttempt(username=username, ip_address=ip))


def failures_since(db: Session, username: str, since: datetime) -> tuple[int, datetime | None]:
    """(number of failures, time of the latest one) for `username` after `since`."""
    count, latest = db.execute(
        select(func.count(), func.max(LoginAttempt.attempted_at))
        .where(LoginAttempt.username == username, LoginAttempt.attempted_at >= since)).one()
    return count, latest


def clear(db: Session, username: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.username == username))
