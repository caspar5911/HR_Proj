"""Attendance / time-tracking API endpoints.

Employees record their own days (clock in/out). Managers and admins see a
team summary plus per-employee detail for a month.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.time_entry import (
    list_team_time_entries_for_month,
    list_time_entries_for_month,
    upsert_time_entry,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.time_entry import (
    MonthAttendance,
    TeamAttendanceRow,
    TimeEntryIn,
    TimeEntryOut,
)
from app.services.audit import record_audit
from app.utils.errors import PermissionDeniedError, ValidationError

router = APIRouter()

# Overtime threshold in hours per day
FULL_DAY_HOURS = 8.0


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _entry_out(entry) -> TimeEntryOut:
    """Build the response schema from an ORM TimeEntry."""
    return TimeEntryOut(
        id=entry.id,
        employee_id=entry.employee_id,
        employee_name=entry.employee_name,
        work_date=entry.work_date,
        clock_in=entry.clock_in,
        clock_out=entry.clock_out,
        breaks_minutes=entry.breaks_minutes,
        notes=entry.notes,
        hours=entry.hours,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _month_attendance(entries) -> MonthAttendance:
    """Wrap a month's entries with its totals."""
    hours_list = [e.hours for e in entries if e.hours is not None]
    total = round(sum(hours_list), 2)
    return MonthAttendance(
        items=[_entry_out(e) for e in entries],
        total_hours=total,
        days_recorded=len(entries),
        avg_daily_hours=round(total / len(hours_list), 2) if hours_list else None,
    )


async def _get_employee_id_for_user(db: AsyncSession, user: User) -> int:
    """Resolve the Employee.id for a given User."""
    result = await db.execute(
        select(Employee).where(Employee.user_id == user.id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise PermissionDeniedError("No employee profile found for your account")
    return emp.id


# ── employee endpoints ──────────────────────────────────────────────────────


@router.get("/me", response_model=MonthAttendance)
async def api_my_month_attendance(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Year of the month"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month of the year"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The signed-in employee's time entries for a month (default: current)."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    emp_id = await _get_employee_id_for_user(db, current_user)
    entries = await list_time_entries_for_month(db, emp_id, year, month)
    return _month_attendance(entries)


@router.post("/me", response_model=TimeEntryOut, status_code=status.HTTP_201_CREATED)
async def api_record_time(
    data: TimeEntryIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clock in / clock out / update today's entry (one row per day)."""
    emp_id = await _get_employee_id_for_user(db, current_user)

    # A same-day clock_out earlier than clock_in is almost always a typo;
    # cross-midnight shifts stay allowed.
    if data.clock_out is not None:
        in_s = data.clock_in.hour * 3600 + data.clock_in.minute * 60
        out_s = data.clock_out.hour * 3600 + data.clock_out.minute * 60
        if out_s == in_s:
            raise ValidationError("clock_out must differ from clock_in")

    entry = await upsert_time_entry(db, emp_id, data)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="time_entry.recorded",
        entity="time_entry",
        entity_id=entry.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return _entry_out(entry)


# ── manager/admin endpoints ─────────────────────────────────────────────────


@router.get("/team", response_model=list[TeamAttendanceRow])
async def api_team_attendance(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Per-employee attendance summary for a month (manager/admin)."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    entries = await list_team_time_entries_for_month(db, year, month)

    by_emp: dict[int, list] = {}
    for e in entries:
        by_emp.setdefault(e.employee_id, []).append(e)

    # Load the involved employees for names/positions.
    emp_ids = sorted(by_emp)
    emps = {}
    if emp_ids:
        result = await db.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        )
        emps = {e.id: e for e in result.scalars().all()}

    rows: list[TeamAttendanceRow] = []
    for emp_id, month_entries in by_emp.items():
        hours_list = [e.hours for e in month_entries if e.hours is not None]
        total = round(sum(hours_list), 2)
        overtime = round(
            sum(max(0.0, h - FULL_DAY_HOURS) for h in hours_list), 2
        )
        emp = emps.get(emp_id)
        name = (
            emp.full_name if emp is not None and hasattr(emp, "full_name")
            else f"#{emp_id}"
        )
        rows.append(
            TeamAttendanceRow(
                employee_id=emp_id,
                employee_name=name,
                position=emp.position if emp is not None else None,
                department=emp.department if emp is not None else None,
                days_recorded=len(month_entries),
                total_hours=total,
                avg_daily_hours=round(total / len(hours_list), 2) if hours_list else None,
                overtime_hours=overtime,
            )
        )

    rows.sort(key=lambda r: r.employee_name)
    return rows


@router.get("/employee/{employee_id}", response_model=MonthAttendance)
async def api_employee_month_attendance(
    employee_id: int,
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    """One employee's time entries for a month (manager/admin)."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    entries = await list_time_entries_for_month(db, employee_id, year, month)
    return _month_attendance(entries)
