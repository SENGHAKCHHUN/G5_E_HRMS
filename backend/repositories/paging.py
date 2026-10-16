"""Run a SELECT one page at a time and also return the total number of matching rows."""
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..core.pagination import ALL, Page


def paginate(db: Session, stmt: Select, page: Page = ALL) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    if page.offset:
        stmt = stmt.offset(page.offset)
    if page.limit is not None:
        stmt = stmt.limit(page.limit)
    return list(db.scalars(stmt).unique()), total
