"""Leave service — business logic for leave management.

Handles balance validation, yearly allocation, employee summaries,
and manager pending-request counts.
"""

from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.utils.errors import InsufficientBalanceError, ValidationError


async def validate_request_balance(
    db: AsyncSession,
    employee_id: int,
    leave_type_id: int,
    days_requested: float,
    year: int | None = None,
) -> None:
    """Validate that the employee has sufficient leave balance.

    Raises ValueError if the employee does not have enough remaining days.
    Also raises if the request dates are in the past.
    """
    # Check for past dates
    today = date.today()
    if year and year < today.year:
        raise ValidationError(f"Leave year {year} is in the past")

    balance = await _get_balance_for_year(db, employee_id, leave_type_id, year)
    if balance:
        if balance.remaining < days_requested:
            remaining = round(balance.remaining, 1)
            raise InsufficientBalanceError(
                f"Insufficient leave balance. Remaining: {remaining} day(s), "
                f"requested: {days_requested} day(s)"
            )


async def get_employee_leave_summary(
    db: AsyncSession,
    employee_id: int,
    year: int | None = None,
) -> dict:
    """Return a leave summary for an employee across all leave types.

    Returns a dict with:
      - year: the year covered
      - types: list of per-type info (name, allocated, used, remaining, carried_over, utilization_pct)
      - total_allocated: sum of all allocated days
      - total_used: sum of all used days
      - total_remaining: sum of all remaining days
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    stmt = (
        select(LeaveBalance)
        .options(
            selectinload(LeaveBalance.leave_type),
            selectinload(LeaveBalance.employee),
        )
        .where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == year,
        )
    )
    result = await db.execute(stmt)
    balances = list(result.scalars().all())

    type_summaries: list[dict] = []
    total_allocated = 0.0
    total_used = 0.0
    total_remaining = 0.0

    for bal in balances:
        remaining = round(bal.remaining, 1)
        utilization = bal.utilization_pct
        total_allocated += bal.allocated
        total_used += bal.used
        total_remaining += remaining

        type_summaries.append({
            "leave_type_id": bal.leave_type_id,
            "leave_type_name": bal.leave_type.name if bal.leave_type else "Unknown",
            "leave_type_color": bal.leave_type.color if bal.leave_type else "#3b82f6",
            "allocated": float(bal.allocated),
            "used": float(bal.used),
            "remaining": remaining,
            "carried_over": float(bal.carried_over),
            "utilization_pct": utilization,
        })

    # Add any active leave types that have no balance record yet
    active_types = await _list_active_leave_types(db)
    existing_type_ids = {bt.leave_type_id for bt in balances}
    for lt in active_types:
        if lt.id not in existing_type_ids:
            type_summaries.append({
                "leave_type_id": lt.id,
                "leave_type_name": lt.name,
                "leave_type_color": lt.color,
                "allocated": float(lt.days_per_year),
                "used": 0.0,
                "remaining": float(lt.days_per_year),
                "carried_over": 0.0,
                "utilization_pct": 0.0,
            })

    type_summaries.sort(key=lambda t: t["leave_type_name"])

    return {
        "year": year,
        "employee_id": employee_id,
        "employee_name": None,  # populated by API if needed
        "types": type_summaries,
        "total_allocated": round(total_allocated, 1),
        "total_used": round(total_used, 1),
        "total_remaining": round(total_remaining, 1),
    }


async def get_manager_pending_count(db: AsyncSession, manager_id: int) -> int:
    """Return the count of pending leave requests from direct reports.

    Only counts requests from employees whose manager_id matches the given manager.
    """
    # Get all direct reports
    result = await db.execute(
        select(Employee).where(Employee.manager_id == manager_id)
    )
    direct_reports = list(result.scalars().all())
    if not direct_reports:
        return 0

    report_ids = {e.id for e in direct_reports}

    count_result = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.employee_id.in_(report_ids),
            LeaveRequest.status == "pending",
        )
    )
    return count_result.scalar() or 0


async def allocate_yearly_balances(
    db: AsyncSession,
    year: int | None = None,
) -> dict:
    """Allocate annual leave balances for all active employees and active leave types.

    For each (employee, leave_type) pair:
      - If a balance record exists for the year, update allocated and carried_over.
      - If no record exists, create a new one.

    Returns a dict with allocation stats.
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    # Fetch all active employees
    emp_result = await db.execute(
        select(Employee).where(Employee.status == "active")
    )
    employees = list(emp_result.scalars().all())

    # Fetch all active leave types
    lt_result = await db.execute(
        select(LeaveType).where(
            LeaveType.active == True,  # noqa: E712
        )
    )
    leave_types = list(lt_result.scalars().all())

    created = 0
    updated = 0

    for emp in employees:
        for lt in leave_types:
            balance = await _get_balance_for_year(db, emp.id, lt.id, year)
            if balance:
                # Update existing record: reset to current year's default
                balance.allocated = float(lt.days_per_year)
                # Keep carried_over from previous year if not explicitly set
                balance.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Create new balance
                balance = LeaveBalance(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    year=year,
                    allocated=float(lt.days_per_year),
                    used=0.0,
                    carried_over=0.0,
                )
                db.add(balance)
                created += 1

    await db.commit()

    # Refresh to get IDs for any created records
    for emp in employees:
        for lt in leave_types:
            stmt = select(LeaveBalance).where(
                LeaveBalance.employee_id == emp.id,
                LeaveBalance.leave_type_id == lt.id,
                LeaveBalance.year == year,
            )
            result = await db.execute(stmt)
            bal = result.scalar_one_or_none()
            if bal:
                await db.refresh(bal)

    return {
        "year": year,
        "employees": len(employees),
        "leave_types": len(leave_types),
        "created": created,
        "updated": updated,
        "total": created + updated,
    }


async def get_remaining_days(
    db: AsyncSession,
    employee_id: int,
    leave_type_id: int,
    year: int | None = None,
) -> dict:
    """Return remaining days for a specific employee and leave type."""
    if year is None:
        year = datetime.now(timezone.utc).year

    balance = await _get_balance_for_year(db, employee_id, leave_type_id, year)
    if balance is None:
        # Check if the leave type exists and return its default
        lt_result = await db.execute(
            select(LeaveType).where(LeaveType.id == leave_type_id)
        )
        leave_type = lt_result.scalar_one_or_none()
        if leave_type:
            return {
                "allocated": float(leave_type.days_per_year),
                "used": 0.0,
                "remaining": float(leave_type.days_per_year),
                "carried_over": 0.0,
            }
        return {
            "allocated": 0.0,
            "used": 0.0,
            "remaining": 0.0,
            "carried_over": 0.0,
        }

    return {
        "allocated": float(balance.allocated),
        "used": float(balance.used),
        "remaining": round(balance.remaining, 1),
        "carried_over": float(balance.carried_over),
    }


# ── Private helpers ────────────────────────────────────────────────────────────


async def _get_balance_for_year(
    db: AsyncSession,
    employee_id: int,
    leave_type_id: int,
    year: int,
) -> LeaveBalance | None:
    """Look up a leave balance record for the given employee, type, and year."""
    result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
    )
    return result.scalar_one_or_none()


async def _list_active_leave_types(db: AsyncSession) -> list[LeaveType]:
    """Return all active leave types, ordered by name."""
    result = await db.execute(
        select(LeaveType)
        .where(LeaveType.active == True)  # noqa: E712
        .order_by(LeaveType.name)
    )
    return list(result.scalars().all())


async def get_department_leaves(
    db: AsyncSession,
    department_id: int,
    year: int | None = None,
) -> list[dict]:
    """Return leave request counts for all employees in a department.

    Useful for department-level leave calendar views.
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    result = await db.execute(
        select(Employee).where(
            Employee.department_id == department_id,  # type: ignore[arg-type]
            Employee.status == "active",
        )
    )
    employees = list(result.scalars().all())

    # Aggregate leave requests by employee
    summary: list[dict] = []
    for emp in employees:
        req_result = await db.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status.in_(["pending", "approved"]),
            )
        )
        requests = list(req_result.scalars().all())

        pending_days = sum(r.days_requested for r in requests if r.status == "pending")
        approved_days = sum(r.days_requested for r in requests if r.status == "approved")

        summary.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "position": emp.position,
            "pending_days": round(pending_days, 1),
            "approved_days": round(approved_days, 1),
            "request_count": len(requests),
        })

    return summary