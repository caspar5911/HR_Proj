"""Leave Balance API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.leave_balance import (
    create_leave_balance,
    get_leave_balance,
    list_leave_balances,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.leave_balance import LeaveBalanceCreate, LeaveBalanceOut

router = APIRouter()


async def _own_employee_id(db: AsyncSession, user: User) -> int | None:
    """Return the ID of the employee record linked to this user, if any."""
    emp = (
        await db.execute(select(Employee).where(Employee.user_id == user.id))
    ).scalar_one_or_none()
    return emp.id if emp else None


@router.get("/", response_model=list[LeaveBalanceOut])
async def api_list_leave_balances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """List leave balances with optional filters.

    Admins/managers may view any employee's balances; a plain employee is
    scoped to their own record and gets 403 when asking for someone else's.
    """
    if current_user.role == UserRole.EMPLOYEE:
        my_id = await _own_employee_id(db, current_user)
        if employee_id is not None and employee_id != my_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own leave balances",
            )
        employee_id = my_id
    balances = await list_leave_balances(
        db, employee_id=employee_id, year=year, skip=skip, limit=limit
    )
    return balances


@router.get("/{employee_id}/{year}", response_model=LeaveBalanceOut)
async def api_get_employee_balance(
    employee_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all leave balances for an employee in a year.

    Employees may only view their own balances.
    """
    if current_user.role == UserRole.EMPLOYEE:
        my_id = await _own_employee_id(db, current_user)
        if my_id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own leave balances",
            )
    balances = await list_leave_balances(db, employee_id=employee_id, year=year)
    if not balances:
        raise HTTPException(status_code=404, detail="No balance found for this employee/year")
    return balances


@router.post("/", response_model=LeaveBalanceOut, status_code=status.HTTP_201_CREATED)
async def api_create_leave_balance(
    data: LeaveBalanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create an initial leave balance allocation (admin only)."""
    # Check if balance already exists
    existing = await get_leave_balance(db, data.employee_id, data.leave_type_id, data.year)
    if existing:
        raise HTTPException(status_code=409, detail="Balance already exists for this employee/year/type")
    return await create_leave_balance(db, data)