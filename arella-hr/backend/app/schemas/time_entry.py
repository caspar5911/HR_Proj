"""Pydantic schemas for the attendance / time-tracking API."""

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TimeEntryIn(BaseModel):
    """Clock in/out payload. ``clock_out`` is null while the day is open."""

    work_date: date
    clock_in: time
    clock_out: Optional[time] = None
    breaks_minutes: int = Field(default=0, ge=0)
    notes: Optional[str] = None


class TimeEntryOut(TimeEntryIn):
    """A recorded day, enriched with the worked-hours total."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    hours: Optional[float]
    created_at: datetime
    updated_at: datetime


class MonthAttendance(BaseModel):
    """One employee's entries for a month plus the month totals."""

    items: list[TimeEntryOut]
    total_hours: float
    days_recorded: int
    avg_daily_hours: Optional[float]


class TeamAttendanceRow(BaseModel):
    """Per-employee summary for the manager attendance view."""

    employee_id: int
    employee_name: str
    position: Optional[str]
    department: Optional[str]
    days_recorded: int
    total_hours: float
    avg_daily_hours: Optional[float]
    overtime_hours: float  # hours beyond 8/day, summed for the month
