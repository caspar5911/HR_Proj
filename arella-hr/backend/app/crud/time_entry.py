"""CRUD operations for the TimeEntry model."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.time_entry import TimeEntry
from app.schemas.time_entry import TimeEntryIn


async def get_time_entry(
    db: AsyncSession,
    employee_id: int,
    work_date: date,
) -> TimeEntry | None:
    """Get one employee's entry for a specific date."""
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date == work_date,
        )
    )
    return result.scalar_one_or_none()


async def upsert_time_entry(
    db: AsyncSession,
    employee_id: int,
    data: TimeEntryIn,
) -> TimeEntry:
    """Create the day's entry, or update it (clock out, breaks, notes).

    One row per employee per day (unique constraint). Clocking in twice on
    the same day re-stamps ``clock_in`` only if the day is still open.
    """
    entry = await get_time_entry(db, employee_id, data.work_date)
    if entry is None:
        entry = TimeEntry(
            employee_id=employee_id,
            work_date=data.work_date,
            clock_in=data.clock_in,
            clock_out=data.clock_out,
            breaks_minutes=data.breaks_minutes,
            notes=data.notes,
        )
        db.add(entry)
    else:
        # A finished day keeps its original clock_in; re-stamping happens
        # only while the day is still open.
        if entry.clock_out is None:
            entry.clock_in = data.clock_in
        if data.clock_out is not None:
            entry.clock_out = data.clock_out
        entry.breaks_minutes = data.breaks_minutes
        if data.notes is not None:
            entry.notes = data.notes
    await db.commit()
    # Re-select so the selectin `employee` relationship is guaranteed loaded.
    return (
        await db.execute(select(TimeEntry).where(TimeEntry.id == entry.id))
    ).scalar_one()


async def list_time_entries_for_month(
    db: AsyncSession,
    employee_id: int,
    year: int,
    month: int,
) -> list[TimeEntry]:
    """All of one employee's entries in a calendar month, oldest first."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    result = await db.execute(
        select(TimeEntry)
        .where(
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date >= start,
            TimeEntry.work_date < end,
        )
        .order_by(TimeEntry.work_date.asc())
    )
    return list(result.scalars().all())


async def list_team_time_entries_for_month(
    db: AsyncSession,
    year: int,
    month: int,
) -> list[TimeEntry]:
    """Every employee's entries in a calendar month (manager view)."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    result = await db.execute(
        select(TimeEntry)
        .where(
            TimeEntry.work_date >= start,
            TimeEntry.work_date < end,
        )
        .order_by(TimeEntry.work_date.asc())
    )
    return list(result.scalars().all())
