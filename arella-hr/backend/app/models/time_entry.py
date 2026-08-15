"""TimeEntry model — daily clock in/out records per employee."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class TimeEntry(Base):
    """ORM model for a single employee's work-day record."""

    __tablename__ = "time_entries"

    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_time_entry_emp_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[time] = mapped_column(Time, nullable=False)
    clock_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    breaks_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    @property
    def hours(self) -> float | None:
        """Worked hours for the day (clock_out − clock_in − breaks).

        A ``clock_out`` earlier than ``clock_in`` is treated as the next
        day (shifts that cross midnight). Returns ``None`` while the day is
        still open (no clock_out yet).
        """
        if self.clock_out is None:
            return None
        delta = _as_timedelta(self.clock_out) - _as_timedelta(self.clock_in)
        if delta < timedelta(0):
            delta += timedelta(days=1)
        delta -= timedelta(minutes=max(0, self.breaks_minutes))
        return max(0.0, round(delta.total_seconds() / 3600, 2))

    @property
    def employee_name(self) -> str:
        """Display name of the employee for this entry."""
        if self.employee is not None:
            return self.employee.full_name if hasattr(self.employee, "full_name") else f"#{self.employee.id}"
        return f"#{self.employee_id}"

    def __repr__(self) -> str:
        return f"<TimeEntry emp={self.employee_id} date={self.work_date}>"


def _as_timedelta(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
