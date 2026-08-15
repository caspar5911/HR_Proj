"""Department API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.department import (
    create_department,
    delete_department,
    get_department,
    list_departments,
    update_department,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.services.audit import diff_changes, record_audit

router = APIRouter()


@router.get("/", response_model=list[DepartmentOut])
async def api_list_departments(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """List all departments."""
    depts = await list_departments(db, skip=skip, limit=limit)
    return depts


@router.get("/{department_id}", response_model=DepartmentOut)
async def api_get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a department by ID."""
    dept = await get_department(db, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def api_create_department(
    data: DepartmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new department (admin only)."""
    # Check for duplicate name
    existing = await list_departments(db)
    if any(d.name == data.name for d in existing):
        raise HTTPException(status_code=409, detail="Department name already exists")
    dept = await create_department(db, data)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="department.created",
        entity="department",
        entity_id=dept.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return dept


@router.put("/{department_id}", response_model=DepartmentOut)
async def api_update_department(
    department_id: int,
    data: DepartmentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a department (admin only)."""
    dept = await get_department(db, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    candidate = data.model_dump(exclude_unset=True)
    old_snapshot = {k: getattr(dept, k, None) for k in candidate}
    changes = diff_changes(old_snapshot, candidate)
    dept = await update_department(db, dept, data)
    if changes is not None:
        await record_audit(
            db,
            user=current_user,
            request=request,
            action="department.updated",
            entity="department",
            entity_id=dept.id,
            changes=changes,
        )
    return dept


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_department(
    department_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a department (admin only)."""
    dept = await get_department(db, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    snapshot = {"name": dept.name}
    await delete_department(db, dept)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="department.deleted",
        entity="department",
        entity_id=department_id,
        changes={"old": snapshot},
    )
    return None