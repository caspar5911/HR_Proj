"""Leave Type API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.leave_type import (
    create_leave_type,
    delete_leave_type,
    get_leave_type,
    list_leave_types,
    update_leave_type,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeOut, LeaveTypeUpdate
from app.services.audit import diff_changes, record_audit

router = APIRouter()


@router.get("/", response_model=list[LeaveTypeOut])
async def api_list_leave_types(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    active_only: bool = Query(True),
):
    """List leave types."""
    types = await list_leave_types(db, skip=skip, limit=limit, active_only=active_only)
    return types


@router.get("/{leave_type_id}", response_model=LeaveTypeOut)
async def api_get_leave_type(
    leave_type_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a leave type by ID."""
    lt = await get_leave_type(db, leave_type_id)
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")
    return lt


@router.post("/", response_model=LeaveTypeOut, status_code=status.HTTP_201_CREATED)
async def api_create_leave_type(
    data: LeaveTypeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new leave type (admin only)."""
    existing = await list_leave_types(db, active_only=False)
    if any(t.name == data.name for t in existing):
        raise HTTPException(status_code=409, detail="Leave type name already exists")
    lt = await create_leave_type(db, data)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_type.created",
        entity="leave_type",
        entity_id=lt.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return lt


@router.put("/{leave_type_id}", response_model=LeaveTypeOut)
async def api_update_leave_type(
    leave_type_id: int,
    data: LeaveTypeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a leave type (admin only)."""
    lt = await get_leave_type(db, leave_type_id)
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")
    candidate = data.model_dump(exclude_unset=True)
    old_snapshot = {k: getattr(lt, k, None) for k in candidate}
    changes = diff_changes(old_snapshot, candidate)
    lt = await update_leave_type(db, lt, data)
    if changes is not None:
        await record_audit(
            db,
            user=current_user,
            request=request,
            action="leave_type.updated",
            entity="leave_type",
            entity_id=lt.id,
            changes=changes,
        )
    return lt


@router.delete("/{leave_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_leave_type(
    leave_type_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Deactivate a leave type (admin only)."""
    lt = await get_leave_type(db, leave_type_id)
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")
    snapshot = {"name": lt.name}
    await delete_leave_type(db, lt)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_type.deleted",
        entity="leave_type",
        entity_id=leave_type_id,
        changes={"old": snapshot},
    )
    return None