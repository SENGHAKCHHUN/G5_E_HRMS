"""Sidebar entries: which screens exist and which roles may open them."""
from core.i18n import N_, _

ALL = {"Admin", "HR Manager", "Employee"}
STAFF = {"Admin", "HR Manager"}

# key, sidebar label (translated when shown), icon, roles, module, class
NAV = [
    ("dashboard", N_("Dashboard"), "dashboard", ALL, "views.dashboard_view", "DashboardView"),
    ("employees", N_("Employee Directory"), "people", STAFF, "views.employee_view", "EmployeeView"),
    ("departments", N_("Departments & Positions"), "org", STAFF, "views.department_view", "DepartmentView"),
    ("attendance", N_("Attendance & Time"), "clock", ALL, "views.attendance_view", "AttendanceView"),
    ("leave", N_("Leave Management"), "calendar", ALL, "views.leave_view", "LeaveView"),
    ("payroll", N_("Payroll & Payslips"), "payroll", ALL, "views.payroll_view", "PayrollView"),
    ("settings", N_("Settings"), "settings", {"Admin"}, "views.settings_view", "SettingsView"),
]
ROLE_NAMES = {"Admin": N_("Admin"), "HR Manager": N_("HR Manager"), "Employee": N_("Employee")}


def role_name(role: str) -> str:
    return _(ROLE_NAMES.get(role, role))
