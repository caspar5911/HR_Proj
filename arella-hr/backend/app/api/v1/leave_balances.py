"""Leave Balance API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.leave_balance import (
    create_leave_balance,
    get_leave_balance,
    list_leave_balances,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.leave_balance import LeaveBalanceCreate, LeaveBalanceOut

router = APIRouter()


@router.get("/", response_model=list[LeaveBalanceOut])
async def api_list_leave_balances(
    db: AsyncSession = Depends(get_db),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """List leave balances with optional filters."""
    balances = await list_leave_balances(
        db, employee_id=employee_id, year=year, skip=skip, limit=limit
    )
    return balances


@router.get("/{employee_id}/{year}", response_model=LeaveBalanceOut)
async def api_get_employee_balance(
    employee_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all leave balances for an employee in a year."""
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