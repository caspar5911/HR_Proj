"""Deduction rule model — reusable deduction definitions."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class DeductionRule(Base):
    """ORM model for a deduction rule (tax, benefits, etc.)."""

    __tablename__ = "deduction_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deduction_type: Mapped[str] = mapped_column(
        String(20), default="fixed", nullable=False
    )  # fixed, percentage
    value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Deduction rules are applied to payroll runs at calculation time. There is no
# per-entry foreign key linking a PayrollEntry to the rule that produced its
# deductions, so no ORM relationship is declared here.