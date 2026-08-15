"""CRUD operations for LeaveBalance model."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.schemas.leave_balance import LeaveBalanceCreate


async def get_leave_balance(
    db: AsyncSession,
    employee_id: int,
    leave_type_id: int,
    year: int,
) -> LeaveBalance | None:
    """Get a leave balance for an employee in a specific year."""
    result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
    )
    return result.scalar_one_or_none()


async def list_leave_balances(
    db: AsyncSession,
    *,
    employee_id: int | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[LeaveBalance]:
    """List leave balances with optional filters."""
    query = select(LeaveBalance).order_by(LeaveBalance.year.desc())

    if employee_id:
        query = query.where(LeaveBalance.employee_id == employee_id)
    if year:
        query = query.where(LeaveBalance.year == year)

    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_leave_balance(db: AsyncSession, data: LeaveBalanceCreate) -> LeaveBalance:
    """Create an initial leave balance allocation."""
    balance = LeaveBalance(
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        year=data.year,
        allocated=data.allocated,
        carried_over=data.carried_over or 0.0,
    )
    db.add(balance)
    await db.commit()
    await db.refresh(balance)
    return balance


async def add_used_days(
    db: AsyncSession,
    balance: LeaveBalance,
    days: float,
) -> LeaveBalance:
    """Add days to the used count (called when a request is approved)."""
    balance.used = round(float(balance.used) + float(days), 1)
    await db.commit()
    await db.refresh(balance)
    return balance


async def remove_used_days(
    db: AsyncSession,
    balance: LeaveBalance,
    days: float,
) -> LeaveBalance:
    """Remove days from the used count (called when a request is cancelled/rejected)."""
    balance.used = round(max(0.0, float(balance.used) - float(days)), 1)
    await db.commit()
    await db.refresh(balance)
    return balance