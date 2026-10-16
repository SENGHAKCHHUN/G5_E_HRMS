"""Database access for system settings (key/value, JSON-encoded)."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Setting


def load_all(db: Session) -> dict:
    """Stored values only. Defaults are applied by the settings service."""
    return {row.key: json.loads(row.value) for row in db.scalars(select(Setting))}


def save(db: Session, key: str, value: object) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=json.dumps(value)))
    else:
        row.value = json.dumps(value)
