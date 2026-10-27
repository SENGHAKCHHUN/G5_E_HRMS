"""Shared types (roles, statuses, time and email formats) and small responses used everywhere."""
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["Admin", "HR Manager", "Employee"]
EmpStatus = Literal["Active", "Probation", "On Leave", "Terminated"]
LeaveType = Literal["Annual", "Sick", "Casual", "Maternity/Paternity", "Unpaid"]
AttStatus = Literal["On Time", "Late", "Absent", "Half Day", "On Leave"]
HHMM = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class PersonFields(BaseModel):
    employee: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None


class EmailSent(BaseModel):
    sent: bool
    to: str | None = None


class Health(BaseModel):
    status: str
    service: str
    version: str
    database: str
