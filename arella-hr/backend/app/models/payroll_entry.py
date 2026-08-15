"""Payroll entry model — one employee's compensation within a payroll run."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class PayrollEntry(Base):
    """ORM model for a single employee's payroll entry within a payroll run."""

    __tablename__ = "payroll_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payroll_run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    gross_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    bonuses: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    deductions: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    payroll_run: Mapped["PayrollRun"] = relationship(
        "PayrollRun", back_populates="entries"
    )

    __table_args__ = (
        Index("ix_payroll_entries_payroll_run_employee", "payroll_run_id", "employee_id"),
    )


# Import here to avoid circular dependency — PayrollRun references PayrollEntry
# (already handled in payroll_run.py)