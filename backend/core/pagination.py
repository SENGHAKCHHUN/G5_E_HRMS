"""Pagination parameters shared by list endpoints (?limit=&offset=)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    limit: int | None = None   # None = all rows
    offset: int = 0


ALL = Page()
