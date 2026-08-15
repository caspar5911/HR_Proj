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
