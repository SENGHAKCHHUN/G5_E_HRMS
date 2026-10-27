"""Employees: create, update, read, summary."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .common import Role, EmpStatus, EMAIL


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
    termination_date: date | None = None  # last working day; set to today when Terminated without one
    position: str | None = None
    salary: int | None = Field(None, ge=0)
    department_id: int | None = None
    status: EmpStatus | None = None
    employment: Literal["Full-time", "Part-time", "Contractor"] | None = None
    work_mode: Literal["HQ Onsite", "Hybrid", "Remote"] | None = None
    shift: str | None = None
    role: Role | None = None


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
    termination_date: date | None = None
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


class EmployeeSummary(BaseModel):
    total: int
    by_status: dict[str, int]
