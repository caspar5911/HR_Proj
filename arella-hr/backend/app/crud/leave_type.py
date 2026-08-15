"""CRUD operations for LeaveType model."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.leave_type import LeaveType
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeUpdate


async def get_leave_type(db: AsyncSession, leave_type_id: int) -> LeaveType | None:
    """Get a leave type by ID."""
    result = await db.execute(
        select(LeaveType).where(LeaveType.id == leave_type_id)
    )
    return result.scalar_one_or_none()


async def list_leave_types(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
) -> list[LeaveType]:
    """List leave types with optional active filter."""
    query = select(LeaveType)
    if active_only:
        query = query.where(LeaveType.active.is_(True))
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_leave_type(db: AsyncSession, data: LeaveTypeCreate) -> LeaveType:
    """Create a new leave type."""
    lt = LeaveType(
        name=data.name,
        description=data.description,
        days_per_year=data.days_per_year or 25.0,
        max_consecutive_days=data.max_consecutive_days or 5,
        is_paid=data.is_paid if data.is_paid is not None else True,
        color=data.color or "#3b82f6",
        requires_approval=data.requires_approval if data.requires_approval is not None else True,
        active=data.active if data.active is not None else True,
    )
    db.add(lt)
    await db.commit()
    await db.refresh(lt)
    return lt


async def update_leave_type(
    db: AsyncSession,
    leave_type: LeaveType,
    data: LeaveTypeUpdate,
) -> LeaveType:
    """Update an existing leave type."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(leave_type, field, value)
    await db.commit()
    await db.refresh(leave_type)
    return leave_type


async def delete_leave_type(db: AsyncSession, leave_type: LeaveType) -> None:
    """Delete a leave type (soft deactivate if still used)."""
    if leave_type.active:
        leave_type.active = False
        await db.commit()
    else:
        await db.delete(leave_type)
        await db.commit()