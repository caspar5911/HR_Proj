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
