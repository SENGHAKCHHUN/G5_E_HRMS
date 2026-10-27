"""Payroll lines, runs, line edits and totals."""
from typing import Literal

from pydantic import BaseModel, Field

from .common import PersonFields


class PayrollOut(PersonFields):
    id: int
    employee_id: int
    month: str
    base_salary: float
    bonus: float
    adjustment: float
    note: str
    paid_days: int | None
    month_days: int
    unpaid_days: float
    unpaid_deduction: float
    overtime_hours: float
    overtime_pay: float
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
    removed: int


class PayrollLineUpdate(BaseModel):
    bonus: float | None = Field(None, ge=0, le=1_000_000_000)
    adjustment: float | None = Field(None, ge=-1_000_000_000, le=1_000_000_000)
    note: str | None = Field(None, max_length=200)


class PayrollPaid(BaseModel):
    month: str
    paid: int


class PayrollSummary(BaseModel):
    count: int
    gross: float
    tax: float
    net: float
    by_status: dict[str, int]
