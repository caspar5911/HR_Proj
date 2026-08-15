"""Payroll run model — a payroll period covering all employees."""

from datetime import date, datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class PayrollRun(Base):
    """ORM model for a payroll run (a single pay period)."""

    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True
    )  # draft, processed, paid
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    entries: Mapped[list["PayrollEntry"]] = relationship(
        "PayrollEntry", back_populates="payroll_run", lazy="selectin"
    )


# Import here to avoid circular dependency — PayrollEntry references PayrollRun
from app.models.payroll_entry import PayrollEntry  # noqa: E402, F401