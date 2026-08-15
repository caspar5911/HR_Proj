"""Employee directory API endpoints."""

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import employee as employee_crud
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListParams,
    EmployeeOut,
    EmployeeOutWithManager,
    EmployeeUpdate,
    PaginatedResponse,
)
from app.services.audit import diff_changes, record_audit

router = APIRouter()


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


# ── list ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(get_current_user)])
async def list_employees_endpoint(
    params: EmployeeListParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return a paginated list of employees with optional filters."""
    items, total = await employee_crud.list_employees(
        db,
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        department=params.department,
        status=params.status,
        position=params.position,
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
async def get_org_tree_endpoint(db: AsyncSession = Depends(get_db)) -> Any:
    """Return the full employee hierarchy as a tree."""
    tree = await employee_crud.get_org_tree(db)
    return [_build_out(e) for e in tree]


# ── detail ───────────────────────────────────────────────────────────────────


@router.get("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(get_current_user)])
async def get_employee_endpoint(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return a single employee by ID."""
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
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
    """Mark an employee as inactive (soft-delete)."""
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    old_status = employee.status
    employee = await employee_crud.deactivate_employee(db, employee)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.deactivated",
        entity="employee",
        entity_id=employee.id,
        changes={"old": {"status": old_status}, "new": {"status": employee.status}},
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
    """Reactivate an inactive employee."""
    employee = await employee_crud.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    old_status = employee.status
    employee = await employee_crud.restore_employee(db, employee)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.restored",
        entity="employee",
        entity_id=employee.id,
        changes={"old": {"status": old_status}, "new": {"status": employee.status}},
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
    """Permanently delete an employee record."""
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
    await employee_crud.delete_employee(db, employee)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="employee.deleted",
        entity="employee",
        entity_id=employee_id,
        changes={"old": snapshot},
    )
    return None