"""Leave requests, reviews and balances."""
from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, model_validator

from ..core.i18n import N_
from .common import LeaveType, PersonFields


class LeaveIn(BaseModel):
    type: LeaveType
    start_date: date
    end_date: date
    reason: str = ""
    employee_id: int | None = None  # staff may file on behalf of someone; defaults to self

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError(N_("End date must be on or after start date"))
        return self


class ReviewIn(BaseModel):
    note: str = ""


class LeaveOut(PersonFields):
    id: int
    employee_id: int
    type: LeaveType
    start_date: date
    end_date: date
    reason: str
    status: Literal["Pending", "Approved", "Rejected"]
    review_note: str
    days: int
    email_queued: bool = False


class LeaveBalanceItem(BaseModel):
    allowance: int
    used: int
    remaining: int
