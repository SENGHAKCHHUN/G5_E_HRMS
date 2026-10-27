"""Departments, positions and hiring requisitions."""
from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from ..core.i18n import N_


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


class RequisitionIn(BaseModel):
    department_id: int
    position_id: int | None = None
    title: str = Field(min_length=1, max_length=100)
    openings: int = Field(1, ge=1, le=100)
    note: str = ""


class RequisitionUpdate(BaseModel):
    status: Literal["Open", "Filled", "Cancelled"]


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
