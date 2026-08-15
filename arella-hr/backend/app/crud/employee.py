"""CRUD operations for the Employee model."""

import math
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee


# ── read ──────────────────────────────────────────────────────────────────────


async def get_employee_by_id(db: AsyncSession, employee_id: int) -> Employee | None:
    """Return a single employee by ID, or None."""
    stmt = (
        select(Employee)
        .options(selectinload(Employee.manager))
        .where(Employee.id == employee_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_employee_by_email(db: AsyncSession, email: str) -> Employee | None:
    """Return a single employee by email, or None."""
    stmt = (
        select(Employee)
        .options(selectinload(Employee.manager))
        .where(Employee.email.ilike(email))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_employees(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    position: Optional[str] = None,
    include_inactive: bool = False,
) -> tuple[list[Employee], int]:
    """Return (items, total_count) with optional filters.

    Pagination is offset-based.  The total_count is computed via a COUNT subquery
    so that the caller can derive total_pages without an extra query.
    """
    conditions: list = []

    if not include_inactive:
        conditions.append(Employee.status != "inactive")

    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Employee.first_name.ilike(search_pattern),
                Employee.last_name.ilike(search_pattern),
                Employee.email.ilike(search_pattern),
            )
        )

    if department:
        conditions.append(Employee.department.ilike(f"%{department}%"))

    if status:
        conditions.append(Employee.status == status)

    if position:
        conditions.append(Employee.position.ilike(f"%{position}%"))

    # ── total count ──────────────────────────────────────────────────────
    count_stmt = select(func.count(Employee.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # ── paginated results ────────────────────────────────────────────────
    stmt = select(Employee)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Employee.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def get_org_tree(db: AsyncSession) -> list[Employee]:
    """Return top-level employees (those without a manager_id).

    Child reports are eagerly loaded via the ``reports`` relationship.
    """
    stmt = (
        select(Employee)
        .options(selectinload(Employee.reports))
        .where(Employee.manager_id.is_(None))
        .order_by(Employee.last_name, Employee.first_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── create ────────────────────────────────────────────────────────────────────


async def create_employee(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    hire_date: Optional[date] = None,
    salary_base: Optional[float] = None,
    address: Optional[str] = None,
    manager_id: Optional[int] = None,
    status: str = "active",
    avatar_url: Optional[str] = None,
) -> Employee:
    """Create and persist a new employee record."""
    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        department=department,
        position=position,
        hire_date=hire_date,
        salary_base=salary_base,
        address=address,
        manager_id=manager_id,
        status=status,
        avatar_url=avatar_url,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


# ── update ────────────────────────────────────────────────────────────────────


async def update_employee(
    db: AsyncSession,
    employee: Employee,
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    hire_date: Optional[date] = None,
    salary_base: Optional[float] = None,
    address: Optional[str] = None,
    manager_id: Optional[int] = None,
    status: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Employee:
    """Update fields on an existing employee record."""
    update_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "department": department,
        "position": position,
        "hire_date": hire_date,
        "salary_base": salary_base,
        "address": address,
        "manager_id": manager_id,
        "status": status,
        "avatar_url": avatar_url,
    }
    for field, value in update_data.items():
        if value is not None:
            setattr(employee, field, value)
    employee.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(employee)
    return employee


# ── delete / deactivate ──────────────────────────────────────────────────────


async def deactivate_employee(db: AsyncSession, employee: Employee) -> Employee:
    """Soft-delete by setting status to 'inactive'."""
    employee.status = "inactive"
    employee.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(employee)
    return employee


async def restore_employee(db: AsyncSession, employee: Employee) -> Employee:
    """Reactivate by setting status back to 'active'."""
    employee.status = "active"
    employee.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(employee)
    return employee


async def delete_employee(db: AsyncSession, employee: Employee) -> None:
    """Hard-delete an employee record (permanent)."""
    await db.delete(employee)
    await db.commit()