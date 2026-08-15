"""CRUD operations for payroll runs and entries."""

import math
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payroll_entry import PayrollEntry
from app.models.payroll_run import PayrollRun
from app.utils.errors import ValidationError


# ── PayrollRun CRUD ──────────────────────────────────────────────────────────


async def get_payroll_run(db: AsyncSession, run_id: int) -> PayrollRun | None:
    """Return a single payroll run by ID, with entries eagerly loaded."""
    stmt = (
        select(PayrollRun)
        .options(selectinload(PayrollRun.entries))
        .where(PayrollRun.id == run_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_payroll_runs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[PayrollRun], int]:
    """Return (items, total_count) with optional filters."""
    conditions: list = []

    if status:
        conditions.append(PayrollRun.status == status)

    if search:
        pattern = f"%{search}%"
        conditions.append(PayrollRun.notes.ilike(pattern))

    # Total count
    count_stmt = select(func.count(PayrollRun.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results
    stmt = select(PayrollRun).options(selectinload(PayrollRun.entries))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(PayrollRun.period_start.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def create_payroll_run(
    db: AsyncSession,
    *,
    period_start: date,
    period_end: date,
    notes: Optional[str] = None,
) -> PayrollRun:
    """Create a new payroll run in 'draft' status."""
    run = PayrollRun(
        period_start=period_start,
        period_end=period_end,
        status="draft",
        notes=notes,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def update_payroll_run(
    db: AsyncSession,
    payroll_run: PayrollRun,
    *,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
) -> PayrollRun:
    """Update fields on an existing payroll run.

    Cannot modify a processed or paid run.
    """
    if payroll_run.status in ("processed", "paid"):
        raise ValidationError("Cannot modify a processed or paid payroll run")

    update_data = {
        "period_start": period_start,
        "period_end": period_end,
        "status": status,
        "notes": notes,
    }
    for field, value in update_data.items():
        if value is not None:
            setattr(payroll_run, field, value)

    payroll_run.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payroll_run)
    return payroll_run


async def delete_payroll_run(db: AsyncSession, payroll_run: PayrollRun) -> None:
    """Permanently delete a payroll run (draft only)."""
    if payroll_run.status not in ("draft",):
        raise ValidationError("Can only delete draft payroll runs")
    await db.delete(payroll_run)
    await db.commit()


# ── PayrollEntry CRUD ─────────────────────────────────────────────────────────


async def list_payroll_entries(
    db: AsyncSession,
    run_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PayrollEntry], int]:
    """Return (items, total_count) for entries in a payroll run."""
    # Total count
    count_stmt = select(func.count(PayrollEntry.id)).where(
        PayrollEntry.payroll_run_id == run_id
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results
    stmt = (
        select(PayrollEntry)
        .where(PayrollEntry.payroll_run_id == run_id)
        .order_by(PayrollEntry.employee_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def get_payroll_entry(db: AsyncSession, entry_id: int) -> PayrollEntry | None:
    """Return a single payroll entry by ID."""
    stmt = select(PayrollEntry).where(PayrollEntry.id == entry_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()