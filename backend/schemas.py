"""Pydantic request/response models."""
from datetime import date
from ipaddress import ip_network
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from .core.i18n import N_  # validation messages are translated in main.validation_error_handler

Role = Literal["Admin", "HR Manager", "Employee"]
EmpStatus = Literal["Active", "Probation", "On Leave", "Terminated"]
LeaveType = Literal["Annual", "Sick", "Casual", "Maternity/Paternity", "Unpaid"]
AttStatus = Literal["On Time", "Late", "Absent", "Half Day", "On Leave"]
HHMM = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ------------------------------------------------------------------ auth


# ------------------------------------------------------------- employees
class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str = Field(pattern=EMAIL)
    phone: str = ""
    gender: Literal["Male", "Female", "Other"] = "Male"
    hire_date: date
    position: str = Field(min_length=1)
    salary: int = Field(ge=0)
    department_id: int
    status: EmpStatus = "Probation"
    employment: Literal["Full-time", "Part-time", "Contractor"] = "Full-time"
    work_mode: Literal["HQ Onsite", "Hybrid", "Remote"] = "HQ Onsite"
    shift: str = "Shift A"


class EmployeeCreate(EmployeeBase):
    role: Role = "Employee"


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=60)
    last_name: str | None = Field(None, min_length=1, max_length=60)
    email: str | None = Field(None, pattern=EMAIL)
    phone: str | None = None
    gender: Literal["Male", "Female", "Other"] | None = None
    hire_date: date | None = None
    position: str | None = None
    salary: int | None = Field(None, ge=0)
    department_id: int | None = None
    status: EmpStatus | None = None
    employment: Literal["Full-time", "Part-time", "Contractor"] | None = None
    work_mode: Literal["HQ Onsite", "Hybrid", "Remote"] | None = None
    shift: str | None = None
    role: Role | None = None


# ----------------------------------------------------------- departments
class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    lead: str = "-"
    location: str = "-"
    budget: int = Field(0, ge=0)
    target: int = Field(0, ge=0)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    lead: str | None = None
    location: str | None = None
    budget: int | None = Field(None, ge=0)
    target: int | None = Field(None, ge=0)


class PositionIn(BaseModel):
    department_id: int
    title: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=10)
    min_salary: int = Field(ge=0)
    max_salary: int = Field(ge=0)
    skills: str = ""
    planned: int = Field(0, ge=0)

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if self.min_salary > self.max_salary:
            raise ValueError(N_("Min salary cannot exceed max salary"))
        return self


# ------------------------------------------------------------ attendance
class ManualAttendance(BaseModel):
    employee_id: int
    date: date
    check_in: str | None = Field(None, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    check_out: str | None = Field(None, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    status: AttStatus


# ----------------------------------------------------------------- leave
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


# -------------------------------------------------------------- settings
class SettingsIn(BaseModel):
    company_name: str | None = None
    domain: str | None = None
    timezone: str | None = None
    work_week: list[str] | None = None
    api_url: str | None = None
    db_url: str | None = None
    jwt_hours: int | None = Field(None, ge=1, le=72)
    enforce_mfa: bool | None = None
    shift_start: str | None = HHMM
    shift_end: str | None = HHMM
    grace_minutes: int | None = Field(None, ge=0, le=120)
    overtime_after: str | None = HHMM
    checkin_open: str | None = HHMM
    checkin_close: str | None = HHMM
    restrict_network: bool | None = None
    office_networks: str | None = None
    remote_exempt: bool | None = None
    tax_rate: float | None = Field(None, ge=0, le=60)
    pension_rate: float | None = Field(None, ge=0, le=30)
    pay_day: int | None = Field(None, ge=1, le=31)
    currency: Literal["USD", "KHR", "EUR", "SGD"] | None = None
    smtp_host: str | None = None
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None   # empty = keep the stored password
    smtp_from: str | None = None
    smtp_tls: bool | None = None
    email_notifications: bool | None = None

    @field_validator("work_week")
    @classmethod
    def valid_days(cls, v: object):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if v is not None and (not v or any(d not in days for d in v)):
            raise ValueError(N_("Pick at least one working day (Mon-Sun)"))
        return v

    @field_validator("smtp_port", "pay_day", "grace_minutes", mode="before")
    @classmethod
    def int_fields_from_str(cls, v: object):
        return int(v) if isinstance(v, str) and v.strip().isdigit() else v

    @field_validator("jwt_hours", mode="before")
    @classmethod
    def int_from_str(cls, v: object):
        return int(v) if isinstance(v, str) and v.isdigit() else v

    @field_validator("office_networks")
    @classmethod
    def valid_networks(cls, v: object):
        if v is None:
            return v
        for part in [p.strip() for p in v.split(",") if p.strip()]:
            try:
                ip_network(part, strict=False)
            except ValueError:
                raise ValueError(f"'{part}' is not a valid IP address or network (e.g. 192.168.1.0/24)")
        return v


# ------------------------------------------------------------- accounts
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def different(self) -> Self:
        if self.current_password == self.new_password:
            raise ValueError(N_("The new password must be different from the current one"))
        if self.new_password.isdigit() or self.new_password.isalpha():
            raise ValueError(N_("Use both letters and numbers in the new password"))
        return self


class OtpCode(BaseModel):
    code: str = Field(pattern=r"^\s*\d{3}\s?\d{3}\s*$")


class PasswordConfirm(BaseModel):
    password: str


# --------------------------------------------------------- requisitions
class RequisitionIn(BaseModel):
    department_id: int
    position_id: int | None = None
    title: str = Field(min_length=1, max_length=100)
    openings: int = Field(1, ge=1, le=100)
    note: str = ""


class RequisitionUpdate(BaseModel):
    status: Literal["Open", "Filled", "Cancelled"]


class TestEmailIn(BaseModel):
    to: str = Field(pattern=EMAIL)


# =====================================================================
# Responses (response_model): what each endpoint returns, shown in /docs
# =====================================================================
class SessionUser(BaseModel):
    user_id: int
    username: str
    role: Role
    employee_id: int | None
    name: str
    initials: str
    department_id: int | None
    department: str
    position: str
    totp_enabled: bool
    mfa_required: bool
    pending_action: str | None = Field(None, description="password_change_required | mfa_setup_required")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: SessionUser


class TwoFactorSetup(BaseModel):
    secret: str = Field(description="Key to enter in the authenticator app")
    uri: str = Field(description="otpauth:// link (for QR codes)")


class EmployeeOut(BaseModel):
    id: int
    code: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    gender: str
    hire_date: date
    position: str
    salary: int
    department_id: int
    department: str
    status: str
    employment: str
    work_mode: str
    shift: str
    role: str | None = None


class EmployeeCreated(EmployeeOut):
    username: str
    initial_password: str = Field(description="One-time password; must be changed at first sign-in")


class DepartmentOut(BaseModel):
    id: int
    name: str
    description: str
    code: str
    lead: str
    location: str
    budget: int
    target: int
    icon: str
    headcount: int
    roles: int
    payroll: int
    avg_seniority: float = Field(description="Average years since hire")
    avg_salary: int


class PositionOut(BaseModel):
    id: int
    department_id: int
    title: str
    grade: str
    min_salary: int
    max_salary: int
    skills: str
    planned: int
    headcount: int


class PersonFields(BaseModel):
    employee: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None


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


class PayrollOut(PersonFields):
    id: int
    employee_id: int
    month: str
    base_salary: float
    bonus: float
    tax: float
    insurance: float
    pension: float
    deductions: float
    net_salary: float
    status: Literal["Pending", "Calculated", "Paid"]
    email: str
    position: str


class PayrollRun(BaseModel):
    month: str
    created: int
    calculated: int


class PayrollPaid(BaseModel):
    month: str
    paid: int


class EmailSent(BaseModel):
    sent: bool
    to: str | None = None


class DashboardStats(BaseModel):
    total_employees: int
    new_this_month: int
    on_leave_today: int
    leave_types: dict[str, int]
    present: int
    on_time: int
    late: int
    expected: int
    attendance_rate: float
    pending_leaves: int
    departments: list[DepartmentOut]
    monthly_payroll: int


class SettingsOut(BaseModel):
    company_name: str
    domain: str
    timezone: str
    work_week: list[str]
    api_url: str
    db_url: str
    jwt_hours: int
    enforce_mfa: bool
    shift_start: str
    shift_end: str
    grace_minutes: int
    overtime_after: str
    checkin_open: str
    checkin_close: str
    restrict_network: bool
    office_networks: str
    remote_exempt: bool
    tax_rate: float
    pension_rate: float
    pay_day: int
    currency: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_from: str
    smtp_tls: bool
    email_notifications: bool
    smtp_password_set: bool = Field(description="The password itself is never returned")


class DatabaseInfo(BaseModel):
    driver: str
    url: str
    size_mb: float | None
    employees: int
    attendance_rows: int
    leave_requests: int
    payroll_rows: int


class AuditEntry(BaseModel):
    when: str
    user: str
    action: str
    detail: str


class UserAccount(BaseModel):
    id: int
    username: str
    role: Role
    employee_id: int | None
    employee: str
    totp_enabled: bool
    must_change_password: bool


class TemporaryPassword(BaseModel):
    username: str
    temporary_password: str


class TwoFactorReset(BaseModel):
    username: str
    totp_enabled: bool


class RequisitionOut(BaseModel):
    id: int
    code: str
    department_id: int
    position_id: int | None
    title: str
    openings: int
    note: str
    status: Literal["Open", "Filled", "Cancelled"]
    created_by: str
    created_at: date


class Health(BaseModel):
    status: str
    service: str
    version: str
    database: str


class EmployeeSummary(BaseModel):
    total: int
    by_status: dict[str, int]


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


class PayrollSummary(BaseModel):
    count: int
    gross: float
    tax: float
    net: float
    by_status: dict[str, int]
