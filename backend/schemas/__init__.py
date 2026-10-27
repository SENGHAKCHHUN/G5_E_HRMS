"""Pydantic request/response models, one file per topic.

Import them from here, e.g. `from ..schemas import EmployeeOut`. Validation messages are marked
with N_ and translated in main.validation_error_handler.

    common.py       Shared types (roles, statuses, time and email formats) and small responses used everywhere.
    accounts.py     Sign-in, passwords, two-factor authentication and user accounts.
    employees.py    Employees: create, update, read, summary.
    departments.py  Departments, positions and hiring requisitions.
    attendance.py   Attendance: manual entries, records, punch policy, monthly summary.
    leave.py        Leave requests, reviews and balances.
    payroll.py      Payroll lines, runs, line edits and totals.
    settings.py     System settings, test email, database information and the audit log.
    dashboard.py    Dashboard figures.
"""
from .common import AttStatus, EMAIL, EmailSent, EmpStatus, HHMM, Health, LeaveType, PersonFields, Role  # noqa: F401
from .accounts import (LoginResponse, OtpCode, PasswordChange, PasswordConfirm, SessionUser,  # noqa: F401
                       TemporaryPassword, TwoFactorReset, TwoFactorSetup, UserAccount)
from .employees import (EmployeeBase, EmployeeCreate, EmployeeCreated, EmployeeOut, EmployeeSummary,  # noqa: F401
                        EmployeeUpdate)
from .departments import (DepartmentIn, DepartmentOut, DepartmentUpdate, PositionIn, PositionOut,  # noqa: F401
                          RequisitionIn, RequisitionOut, RequisitionUpdate)
from .attendance import AttendanceOut, AttendanceSummary, ManualAttendance, PunchPolicy  # noqa: F401
from .leave import LeaveBalanceItem, LeaveIn, LeaveOut, ReviewIn  # noqa: F401
from .payroll import PayrollLineUpdate, PayrollOut, PayrollPaid, PayrollRun, PayrollSummary  # noqa: F401
from .settings import AuditEntry, DatabaseInfo, SettingsIn, SettingsOut, TestEmailIn  # noqa: F401
from .dashboard import DashboardStats  # noqa: F401
