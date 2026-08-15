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

    @property
    def leave_type_name(self) -> str:
        """Display name of the leave type for this balance."""
        return self.leave_type.name if self.leave_type is not None else ""

    def __repr__(self) -> str:
        return f"<LeaveBalance emp={self.employee_id} type={self.leave_type_id} year={self.year}>"
