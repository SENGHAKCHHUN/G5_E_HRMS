"""System settings, test email, database information and the audit log."""
from ipaddress import ip_network
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..core.i18n import N_
from .common import HHMM, EMAIL


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
    auto_absent: bool | None = None
    auto_checkout: bool | None = None
    half_day_hours: float | None = Field(None, ge=0, le=12)
    checkout_cutoff: str | None = HHMM
    tax_rate: float | None = Field(None, ge=0, le=60)
    tax_brackets: str | None = Field(None, max_length=300)
    tax_bonus: bool | None = None
    pension_rate: float | None = Field(None, ge=0, le=30)
    insurance_amount: float | None = Field(None, ge=0)
    insurance_high_amount: float | None = Field(None, ge=0)
    insurance_threshold: float | None = Field(None, ge=0)
    deduct_unpaid: bool | None = None
    overtime_rate: float | None = Field(None, ge=0, le=5)
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


class TestEmailIn(BaseModel):
    to: str = Field(pattern=EMAIL)


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
    auto_absent: bool
    auto_checkout: bool
    half_day_hours: float
    checkout_cutoff: str
    tax_rate: float
    tax_brackets: str
    tax_bonus: bool
    pension_rate: float
    insurance_amount: float
    insurance_high_amount: float
    insurance_threshold: float
    deduct_unpaid: bool
    overtime_rate: float
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
