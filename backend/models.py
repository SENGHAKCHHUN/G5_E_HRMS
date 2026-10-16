"""SQLAlchemy table models (see 'Database Design' in README.md)."""
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    code: Mapped[str] = mapped_column(String(30), default="")
    lead: Mapped[str] = mapped_column(String(100), default="-")
    location: Mapped[str] = mapped_column(String(100), default="-")
    budget: Mapped[int] = mapped_column(Integer, default=0)
    target: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str] = mapped_column(String(40), default="department")

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")
    positions: Mapped[list["Position"]] = relationship(back_populates="department",
                                                      cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    title: Mapped[str] = mapped_column(String(100))
    grade: Mapped[str] = mapped_column(String(10))
    min_salary: Mapped[int] = mapped_column(Integer)
    max_salary: Mapped[int] = mapped_column(Integer)
    skills: Mapped[str] = mapped_column(String(200), default="")
    planned: Mapped[int] = mapped_column(Integer, default=0)

    department: Mapped[Department] = relationship(back_populates="positions")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    gender: Mapped[str] = mapped_column(String(10), default="Male")
    hire_date: Mapped[date] = mapped_column(Date)
    position: Mapped[str] = mapped_column(String(100))
    salary: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    status: Mapped[str] = mapped_column(String(20), default="Active")
    employment: Mapped[str] = mapped_column(String(20), default="Full-time")
    work_mode: Mapped[str] = mapped_column(String(20), default="HQ Onsite")
    shift: Mapped[str] = mapped_column(String(30), default="Shift A")

    department: Mapped[Department] = relationship(back_populates="employees")
    user: Mapped["User | None"] = relationship(back_populates="employee", cascade="all, delete-orphan")
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="employee",
                                                          cascade="all, delete-orphan")
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="employee",
                                                                cascade="all, delete-orphan")
    payroll: Mapped[list["Payroll"]] = relationship(back_populates="employee", cascade="all, delete-orphan")

    @property
    def code(self) -> str:
        return f"EMP-{self.id:03d}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # Admin | HR Manager | Employee
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), unique=True)
    # set for new accounts and after an admin reset: the user must pick a new password
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # two-factor authentication (TOTP, authenticator apps)
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    employee: Mapped[Employee | None] = relationship(back_populates="user")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[time | None] = mapped_column(Time)
    check_out: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20))  # On Time | Late | Absent | Half Day | On Leave
    source: Mapped[str] = mapped_column(String(20), default="self")  # self | manual
    ip_address: Mapped[str] = mapped_column(String(45), default="")

    employee: Mapped[Employee] = relationship(back_populates="attendance")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    review_note: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped[Employee] = relationship(back_populates="leave_requests")


class Payroll(Base):
    __tablename__ = "payroll"
    __table_args__ = (UniqueConstraint("employee_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    base_salary: Mapped[float] = mapped_column(Float)
    bonus: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    insurance: Mapped[float] = mapped_column(Float, default=0)
    pension: Mapped[float] = mapped_column(Float, default=0)
    deductions: Mapped[float] = mapped_column(Float, default=0)
    net_salary: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending | Calculated | Paid

    employee: Mapped[Employee] = relationship(back_populates="payroll")


class Setting(Base):
    """Key/value store for system settings (value is JSON-encoded)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    username: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text, default="")


class Requisition(Base):
    """A request to hire for a job role (opened from Departments & Positions)."""
    __tablename__ = "requisitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(100))
    openings: Mapped[int] = mapped_column(Integer, default=1)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Open")  # Open | Filled | Cancelled
    created_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LoginAttempt(Base):
    """Failed sign-ins, used to temporarily lock an account after repeated failures."""
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    ip_address: Mapped[str] = mapped_column(String(45), default="")
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
