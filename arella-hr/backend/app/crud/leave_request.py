"""CRUD operations for LeaveRequest model."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.leave_request import LeaveRequest
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestUpdate
from app.utils.errors import ValidationError


def compute_days(start_date, end_date, leave_type: LeaveType) -> float:
    """Compute the number of days between two dates, respecting max_consecutive_days."""
    delta = (end_date - start_date).days + 1  # inclusive
    if leave_type.max_consecutive_days and delta > leave_type.max_consecutive_days:
        delta = float(leave_type.max_consecutive_days)
    # Use float for half-day support in the future
    return float(delta)


async def get_leave_request(db: AsyncSession, request_id: int) -> LeaveRequest | None:
    """Get a leave request by ID with eager relationships."""
    result = await db.execute(
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_type),
            selectinload(LeaveRequest.department),
            selectinload(LeaveRequest.approver),
        )
        .where(LeaveRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def list_leave_requests(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    leave_type_id: int | None = None,
    employee_id: int | None = None,
) -> tuple[list[LeaveRequest], int]:
    """List leave requests with optional filters. Returns (items, total_count)."""
    base_query = select(LeaveRequest).order_by(LeaveRequest.created_at.desc())

    if status:
        base_query = base_query.where(LeaveRequest.status == status)
    if leave_type_id:
        base_query = base_query.where(LeaveRequest.leave_type_id == leave_type_id)
    if employee_id:
        base_query = base_query.where(LeaveRequest.employee_id == employee_id)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    result = await db.execute(
        base_query.offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def create_leave_request(
    db: AsyncSession,
    data: LeaveRequestCreate,
    employee_id: int,
    department_id: int | None,
) -> LeaveRequest:
    """Create a new leave request (status defaults to pending)."""
    # Resolve leave type to compute days
    lt_result = await db.execute(
        select(LeaveType).where(LeaveType.id == data.leave_type_id)
    )
    leave_type = lt_result.scalar_one_or_none()
    if not leave_type:
        raise ValidationError(f"Leave type {data.leave_type_id} not found")

    days_requested = compute_days(data.start_date, data.end_date, leave_type)

    req = LeaveRequest(
        employee_id=employee_id,
        leave_type_id=data.leave_type_id,
        department_id=department_id,
        start_date=data.start_date,
        end_date=data.end_date,
        days_requested=days_requested,
        reason=data.reason,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def approve_leave_request(
    db: AsyncSession,
    request: LeaveRequest,
    data: LeaveRequestUpdate,
    approver_id: int,
) -> LeaveRequest:
    """Approve a leave request and update the employee's leave balance."""
    if request.status != "pending":
        raise ValidationError(f"Request is already {request.status}")

    # Update status and approver
    request.status = "approved"
    request.approved_by = approver_id
    if data.manager_note:
        request.manager_note = data.manager_note

    # Update leave balance (add to used)
    balance = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == request.employee_id,
            LeaveBalance.leave_type_id == request.leave_type_id,
            LeaveBalance.year == request.start_date.year,
        )
    )
    balance = balance.scalar_one_or_none()
    if balance:
        balance.used = round(balance.used + request.days_requested, 1)
        await db.commit()
    else:
        # No balance record yet — just commit the request
        pass

    await db.commit()
    await db.refresh(request)
    return request


async def reject_leave_request(
    db: AsyncSession,
    request: LeaveRequest,
    data: LeaveRequestUpdate,
) -> LeaveRequest:
    """Reject a leave request."""
    if request.status != "pending":
        raise ValidationError(f"Request is already {request.status}")

    request.status = "rejected"
    if data.manager_note:
        request.manager_note = data.manager_note

    await db.commit()
    await db.refresh(request)
    return request


async def cancel_leave_request(
    db: AsyncSession,
    request: LeaveRequest,
) -> LeaveRequest:
    """Cancel (delete) a leave request, refunding days from balance if approved."""
    if request.status == "approved":
        # Refund days
        balance = await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == request.employee_id,
                LeaveBalance.leave_type_id == request.leave_type_id,
                LeaveBalance.year == request.start_date.year,
            )
        )
        balance = balance.scalar_one_or_none()
        if balance:
            balance.used = round(max(0.0, balance.used - request.days_requested), 1)

    await db.delete(request)
    await db.commit()
    return request