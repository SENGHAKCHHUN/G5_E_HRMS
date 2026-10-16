"""Bring the database schema up to date with Alembic at start-up."""
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect, text

from .config import BACKEND_DIR
from .database import Base, engine
from .logging import get_logger

log = get_logger("migrations")
ALEMBIC_INI = BACKEND_DIR.parent / "alembic.ini"
BASELINE = "0001"  # the first migration = the schema of databases created before Alembic


def upgrade_database() -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["configure_logger"] = False  # keep the app's logging setup
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "users" in tables and "alembic_version" not in tables:
            log.info("Database created before migrations were introduced: bringing it to the baseline")
            _bring_legacy_database_to_baseline(conn)
            command.stamp(cfg, BASELINE)
        command.upgrade(cfg, "head")


def _bring_legacy_database_to_baseline(conn: Connection):
    """One-time bridge for databases made with create_all(): add missing tables and columns."""
    from .. import models  # importing the models registers every table on the metadata
    models.Base.metadata.create_all(bind=conn)
    insp = inspect(conn)
    for table in Base.metadata.sorted_tables:
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            ddl = col.type.compile(dialect=conn.dialect)
            default = col.default.arg if col.default is not None and not callable(col.default.arg) else None
            clause = f" DEFAULT {int(default) if isinstance(default, bool) else repr(default)}" \
                if default is not None else ""
            conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}{clause}"))
            log.info("Added column %s.%s", table.name, col.name)
