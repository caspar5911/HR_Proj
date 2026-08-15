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
from app.models.payroll_run import PayrollRun  # noqa: F401
from app.models.payroll_entry import PayrollEntry  # noqa: F401
from app.models.deduction_rule import DeductionRule  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.time_entry import TimeEntry  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.review import ReviewCycle, Review  # noqa: F401

__all__ = [
    "Base", "User", "UserRole", "Employee", "Department",
    "LeaveType", "LeaveBalance", "LeaveRequest",
    "PayrollRun", "PayrollEntry", "DeductionRule", "AuditLog",
    "TimeEntry", "Notification", "ReviewCycle", "Review",
]
