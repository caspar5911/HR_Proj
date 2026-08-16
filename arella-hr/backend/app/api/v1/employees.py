"""Employee directory API endpoints."""

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import employee as employee_crud
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.payroll_entry import PayrollEntry
from app.models.payroll_run import PayrollRun
from app.models.user import User, UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListParams,
    EmployeeOut,
    EmployeeOutWithManager,
    EmployeeUpdate,
    PaginatedResponse,
)
from app.schemas.payroll_run import PayslipOut
from app.services.audit import diff_changes, record_audit
from app.utils.errors import PermissionDeniedError

router = APIRouter()

# Roles that may see the whole directory (vs. plain employees, who are
# scoped to their own record everywhere in this router).
STAFF_ROLES = (UserRole.ADMIN, UserRole.MANAGER)


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


# ── helpers ──────────────────────────────────────────────────────────────────


def _build_out(emp: Employee) -> EmployeeOut:
    """Convert an Employee ORM instance to the response schema,
    resolving the manager's display name eagerly."""
    manager_name: str | None = None
    if emp.manager_id is not None and hasattr(emp, "manager") and emp.manager:
        manager_name = emp.manager.full_name
    return EmployeeOut(
        id=emp.id,
        first_name=emp.first_name,
        last_name=emp.last_name,
        email=emp.email,
        phone=emp.phone,
        department=emp.department,
        position=emp.position,
        hire_date=emp.hire_date,
        salary_base=float(emp.salary_base) if emp.salary_base is not None else None,
        address=emp.address,
        manager_id=emp.manager_id,
        manager_name=manager_name,
        status=emp.status,
        avatar_url=emp.avatar_url,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )


async def _sync_linked_user_active(
    db: AsyncSession, user_id: int | None, active: bool
) -> bool:
    """Bring the linked login account in line with the employee's status.

    Deactivating/offboarding an employee must not leave a working login
    behind. Returns True when an account's state actually changed (callers
    use it to enrich the audit entry).
    """
    if user_id is None:
        return False
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None or user.is_active == active:
        return False
    user.is_active = active
    await db.commit()
    await db.refresh(user)
    return True


# ── list ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(get_current_user)])
async def list_employees_endpoint(
    params: EmployeeListParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return a paginated list of employees with optional filters.

    Access control: admins/managers see the full directory. Plain employees
    are scoped to their own record — the directory carries PII and salary,
    which must not be enumerable by any authenticated user.
    """
    scoped_to_user = None if _is_staff(current_user) else current_user.id
    items, total = await employee_crud.list_employees(
        db,
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        department=params.department,
        status=params.status,
        position=params.position,
        include_inactive=params.include_inactive,
        user_id=scoped_to_user,
    )
    total_pages = math.ceil(total / params.page_size) if total else 0

    return PaginatedResponse(
        items=[_build_out(emp) for emp in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


# ── tree (org chart) ────────────────────────────────────────────────────────


@router.get(
    "/org-tree",
    response_model=list[EmployeeOutWithManager],
    dependencies=[Depends(get_current_user)],
)
async def get_org_tree_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return the full employee hierarchy as a tree (staff only)."""
    if not _is_staff(current_user):
        raise PermissionDeniedError(
            "The org chart is only available to managers and admins"
        )
    tree = await employee_crud.get_org_tree(db)
    return [_build_out(e) for e in tree]


# ── my profile (self-service) ───────────────────────────────────────────────


@router.get("/me", response_model=EmployeeOut, dependencies=[Depends(get_current_user)])
async def get_my_profile_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return the employee record linked to the signed-in user.

    Powers the employee self-service "My Home" page. Returns 404 when the
    account has no linked directory record.
    """
    # Explicit selectinload: the self-referential `manager` relationship does
    # not honor its declared lazy strategy (SQLAlchemy defers it to first
    # access, which fails under async). _build_out reads emp.manager.
    employee = (
        await db.execute(
            select(Employee)
            .options(selectinload(Employee.manager))
            .where(Employee.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No employee profile is linked to this account",
        )
    return _build_out(employee)


# ── payslips (pay history) ──────────────────────────────────────────────────


@router.get(
    "/{employee_id}/payslips",
    response_model=list[PayslipOut],
    dependencies=[Depends(get_current_user)],
)
async def get_payslips_endpoint(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return an employee's pay history as payslips, newest period first.

    Access control: admins/managers may view any employee; a plain employee
    may only view their own payslips.
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        my_profile = (
            await db.execute(select(Employee).where(Employee.user_id == current_user.id))
        ).scalar_one_or_none()
        if my_profile is None or my_profile.id != employee_id:
            raise PermissionDeniedError("You can only view your own payslips")

    # Processed/paid runs only — draft runs have no trustworthy figures yet.
    entries = (
        await db.execute(
            select(PayrollEntry)
            .options(selectinload(PayrollEntry.payroll_run))
            .where(PayrollEntry.employee_id == employee_id)
            .order_by(PayrollEntry.created_at.desc())
        )
    ).scalars().all()

    slips: list[PayslipOut] = []
    for entry in entries:
        run = entry.payroll_run
        if run is None or run.status not in ("processed", "paid"):
            continue
        slips.append(
            PayslipOut(
                entry_id=entry.id,
                run_id=run.id,
                period_start=run.period_start,
                period_end=run.period_end,
                run_status=run.status,
                employee_id=employee.id,
                employee_name=employee.full_name,
                position=employee.position,
                department=employee.department,
                gross_salary=float(entry.gross_salary),
                bonuses=float(entry.bonuses),
                deductions=float(entry.deductions),
                net_pay=float(entry.net_pay),
                notes=entry.notes,
                generated_at=run.generated_at,
            )
        )
    return slips


# ── detail ───────────────────────────────────────────────────────────────────


@router.get("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(get_current_user)])
async def get_employee_endpoint(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return a single employee by ID.

    Admins/managers may read any record; a plain employee may only read
    their own (same rule as the payslips endpoint below).
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if not _is_staff(current_user):
        my_profile = (
            await db.execute(select(Employee).where(Employee.user_id == current_user.id))
        ).scalar_one_or_none()
        if my_profile is None or my_profile.id != employee_id:
            raise PermissionDeniedError("You can only view your own employee record")

    return _build_out(employee)


# ── create ──────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def create_employee_endpoint(
    payload: EmployeeCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new employee record."""
    # Check for duplicate email
    existing = await employee_crud.get_employee_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this email already exists",
        )

    # Validate manager_id refers to an existing employee (if provided)
    if payload.manager_id is not None:
        manager = await employee_crud.get_employee_by_id(db, payload.manager_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager not found",
            )

    employee = await employee_crud.create_employee(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        department=payload.department,
        position=payload.position,
        hire_date=payload.hire_date,
        salary_base=payload.salary_base,
        address=payload.address,
        manager_id=payload.manager_id,
        status=payload.status,
        avatar_url=payload.avatar_url,
    )
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.created",
        entity="employee",
        entity_id=employee.id,
        changes={"new": payload.model_dump(mode="json")},
    )
    return _build_out(employee)


# ── update ──────────────────────────────────────────────────────────────────


@router.put(
    "/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def update_employee_endpoint(
    employee_id: int,
    payload: EmployeeUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing employee record.

    Only non-None fields in the payload are applied.
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    # Check email uniqueness if email is being changed
    if payload.email is not None and payload.email.lower() != employee.email.lower():
        existing = await employee_crud.get_employee_by_email(db, payload.email)
        if existing and existing.id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An employee with this email already exists",
            )

    # Validate manager_id
    if payload.manager_id is not None and payload.manager_id != employee_id:
        manager = await employee_crud.get_employee_by_id(db, payload.manager_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager not found",
            )

    candidate = payload.model_dump(exclude_unset=True)
    old_snapshot = {k: getattr(employee, k, None) for k in candidate}
    changes = diff_changes(old_snapshot, candidate)

    employee = await employee_crud.update_employee(
        db,
        employee,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        department=payload.department,
        position=payload.position,
        hire_date=payload.hire_date,
        salary_base=payload.salary_base,
        address=payload.address,
        manager_id=payload.manager_id,
        status=payload.status,
        avatar_url=payload.avatar_url,
    )
    if changes is not None:
        await record_audit(
            db,
            user=current_user,
            request=request,
            action="employee.updated",
            entity="employee",
            entity_id=employee.id,
            changes=changes,
        )
    return _build_out(employee)


# ── deactivate / restore ────────────────────────────────────────────────────


@router.patch(
    "/{employee_id}/deactivate",
    response_model=EmployeeOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def deactivate_employee_endpoint(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Mark an employee as inactive (soft-delete).

    Also disables the linked login account, so a leaver cannot keep
    authenticating and using the self-service endpoints.
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    old_status = employee.status
    employee = await employee_crud.deactivate_employee(db, employee)
    user_deactivated = await _sync_linked_user_active(db, employee.user_id, active=False)

    changes: dict = {"old": {"status": old_status}, "new": {"status": employee.status}}
    if user_deactivated:
        changes["user_account"] = "deactivated"
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.deactivated",
        entity="employee",
        entity_id=employee.id,
        changes=changes,
    )
    return _build_out(employee)


@router.patch(
    "/{employee_id}/restore",
    response_model=EmployeeOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def restore_employee_endpoint(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reactivate an inactive employee.

    Symmetric with deactivation: the linked login account is re-enabled too
    (it was disabled when the employee was deactivated).
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    old_status = employee.status
    employee = await employee_crud.restore_employee(db, employee)
    user_reactivated = await _sync_linked_user_active(db, employee.user_id, active=True)

    changes: dict = {"old": {"status": old_status}, "new": {"status": employee.status}}
    if user_reactivated:
        changes["user_account"] = "reactivated"
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.restored",
        entity="employee",
        entity_id=employee.id,
        changes=changes,
    )
    return _build_out(employee)


# ── delete (hard) ───────────────────────────────────────────────────────────


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_employee_endpoint(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete an employee record.

    Also disables the linked login account — deleting the directory record
    must not leave a working login behind (same rule as deactivation).
    """
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    snapshot = {
        "email": employee.email,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "department": employee.department,
        "status": employee.status,
    }
    linked_user_id = employee.user_id
    await employee_crud.delete_employee(db, employee)
    user_deactivated = await _sync_linked_user_active(db, linked_user_id, active=False)

    changes: dict = {"old": snapshot}
    if user_deactivated:
        changes["user_account"] = "deactivated"
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.deleted",
        entity="employee",
        entity_id=employee_id,
        changes=changes,
    )
    return None