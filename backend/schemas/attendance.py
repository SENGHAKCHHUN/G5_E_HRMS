"""Attendance: manual entries, records, punch policy, monthly summary."""
from datetime import date

from pydantic import BaseModel, Field

from .common import AttStatus, PersonFields


class ManualAttendance(BaseModel):
    employee_id: int
    date: date
    check_in: str | None = Field(None, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    check_out: str | None = Field(None, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    status: AttStatus


class AttendanceOut(PersonFields):
    id: int | None = None
    employee_id: int
    date: date
    check_in: str | None = Field(None, description="HH:MM:SS (server time)")
    check_out: str | None = None
    status: AttStatus
    source: str | None = Field(None, description="self | manual | seed")
    shift: str | None = None


class PunchPolicy(BaseModel):
    server_time: str
    ip: str
    restrict_network: bool
    on_office_network: bool
    remote_exempt: bool
    network_ok: bool
    checkin_open: str
    checkin_close: str
    window_open: bool
    work_day: bool
    shift_start: str
    grace_minutes: int


class AttendanceSummary(BaseModel):
    records: int
    worked_days: int
    on_time: int
    late: int
    absent: int
    half_day: int
    on_leave: int
    completed_shifts: int
    avg_seconds: float = Field(description="Average length of completed shifts")
