"""Dashboard figures."""
from pydantic import BaseModel

from .departments import DepartmentOut


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
