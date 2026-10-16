"""Database engine, session factory and ORM base class.

Change HRMS_DATABASE_URL to switch databases (see README.md), e.g.
    postgresql://user:password@localhost:5432/hr_system
    mysql+pymysql://user:password@localhost:3306/hr_system
Schema changes are managed with Alembic (see backend/migrations).
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import config

DATABASE_URL = config.database_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def is_sqlite() -> bool:
    return DATABASE_URL.startswith("sqlite:///")


def sqlite_path() -> str:
    return DATABASE_URL.replace("sqlite:///", "", 1)


def ping() -> bool:
    """True when the database answers (used by the health check)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - any failure means unhealthy
        return False
