"""CRUD operations for Department model."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


async def get_department(db: AsyncSession, department_id: int) -> Department | None:
    """Get a department by ID with eager-loaded relationships."""
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.manager), selectinload(Department.employees))
        .where(Department.id == department_id)
    )
    return result.scalar_one_or_none()


async def list_departments(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Department]:
    """List all departments with pagination."""
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.manager))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_department(db: AsyncSession, data: DepartmentCreate) -> Department:
    """Create a new department."""
    dept = Department(
        name=data.name,
        description=data.description,
        manager_id=data.manager_id,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


async def update_department(
    db: AsyncSession,
    department: Department,
    data: DepartmentUpdate,
) -> Department:
    """Update an existing department."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)
    await db.commit()
    await db.refresh(department)
    return department


async def delete_department(db: AsyncSession, department: Department) -> None:
    """Delete a department."""
    await db.delete(department)
    await db.commit()