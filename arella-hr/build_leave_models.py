#!/usr/bin/env python3
"""Build all Leave & Attendance backend files: models, schemas, CRUD, API, frontend client."""
import os

base = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def write_file(rel_path, content):
    full = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    print(f"  wrote {rel_path}")

# ── 1. Department model ──────────────────────────────────────────────

write_file("backend/app/models/department.py", '''\
"""Department model — organisational units."""

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.models import Base


class Department(Base):
    """ORM model for departments."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    manager: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[manager_id], lazy="selectin"
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="department_obj", lazy="selectin"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="department", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
''')

# ── 2. LeaveType model ──────────────────────────────────────────────

write_file("backend/app/models/leave_type.py", '''\
"""LeaveType model — configurable leave categories."""

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

from app.models import Base


class LeaveType(Base):
    """ORM model for leave type configurations."""

    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    days_per_year: Mapped[float] = mapped_column(Numeric(5, 1), default=25.0)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, default=5)
    is_paid: Mapped[bool] = mapped_column(default=True)
    color: Mapped[str] = mapped_column(String(7), default="#3b82f6")
    requires_approval: Mapped[bool] = mapped_column(default=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<LeaveType {self.name}>"
''')

# ── 3. LeaveBalance model ──────────────────────────────────────────────

write_file("backend/app/models/leave_balance.py", '''\
"""LeaveBalance model — per-employee leave allocation tracking."""

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.models import Base


class LeaveBalance(Base):
    """ORM model for tracking annual leave allocations per employee."""

    __tablename__ = "leave_balances"

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_employee_leave_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type_id: Mapped[int] = mapped_column(
        ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Allocated (total entitlement)
    allocated: Mapped[float] = mapped_column(Numeric(6, 1), default=0.0)
    # Days already used (approved requests within this year)
    used: Mapped[float] = mapped_column(Numeric(6, 1), default=0.0)
    # Carried over from previous year
    carried_over: Mapped[float] = mapped_column(Numeric(6, 1), default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    leave_type: Mapped["LeaveType"] = relationship("LeaveType", lazy="selectin")

    @property
    def remaining(self) -> float:
        """Days remaining in this allocation."""
        return max(0.0, self.allocated + self.carried_over - self.used)

    @property
    def utilization_pct(self) -> float:
        """Percentage of allocated leave already used."""
        total = self.allocated + self.carried_over
        if total <= 0:
            return 0.0
        return round(min(100.0, (self.used / total) * 100), 1)

    def __repr__(self) -> str:
        return f"<LeaveBalance emp={self.employee_id} type={self.leave_type_id} year={self.year}>"
''')

# ── 4. LeaveRequest model ──────────────────────────────────────────────

write_file("backend/app/models/leave_request.py", '''\
"""LeaveRequest model — individual leave requests."""

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime, timezone

from app.models import Base


class LeaveRequest(Base):
    """ORM model for employee leave requests."""

    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type_id: Mapped[int] = mapped_column(
        ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
    days_requested: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, approved, rejected
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    manager_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    leave_type: Mapped["LeaveType"] = relationship("LeaveType", lazy="selectin")
    department: Mapped["Department"] = relationship(
        "Department", back_populates="leave_requests", lazy="selectin"
    )
    approver: Mapped["User | None"] = relationship("User", lazy="selectin")

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    def __repr__(self) -> str:
        return f"<LeaveRequest emp={self.employee_id} type={self.leave_type_id} status={self.status}>"
''')

# ── 5. Update models/__init__.py ──────────────────────────────────────────────

write_file("backend/app/models/__init__.py", '''\
"""SQLAlchemy declarative base and model imports.

All domain models MUST be imported here so Alembic can auto-discover them
during migration generation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# -- import every domain model --

from app.models.user import User, UserRole  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.leave_type import LeaveType  # noqa: F401
from app.models.leave_balance import LeaveBalance  # noqa: F401
from app.models.leave_request import LeaveRequest  # noqa: F401

__all__ = ["Base", "User", "UserRole", "Employee", "Department", "LeaveType", "LeaveBalance", "LeaveRequest"]
''')

# ── 6. Update employee.py with department_obj relationship ──────────────────────

emp_model_path = os.path.join(base, "backend/app/models/employee.py")
with open(emp_model_path, "r") as f:
    emp_content = f.read()

if "department_obj" not in emp_content:
    emp_content = emp_content.replace(
        '    @property\n    def full_name',
        '    # Department association\n    department_obj: Mapped["Department | None"] = relationship(\n        "Department", back_populates="employees", lazy="selectin"\n    )\n\n    @property\n    def full_name'
    )
    with open(emp_model_path, "w") as f:
        f.write(emp_content)
    print("  updated employee.py with department_obj relationship")

print("\n--- Models complete ---")