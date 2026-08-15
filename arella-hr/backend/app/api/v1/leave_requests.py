"""Leave Request API endpoints."""

import math

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.leave_request import (
    approve_leave_request,
    cancel_leave_request,
    create_leave_request,
    get_leave_request,
    list_leave_requests,
    reject_leave_request,
)
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.leave_request import (
    LeaveRequestCreate,
    LeaveRequestListParams,
    LeaveRequestOut,
    LeaveRequestUpdate,
    PaginatedLeaveResponse,
)
from app.services.audit import record_audit
from app.services.email import notify_leave_decided, notify_leave_requested
from app.utils.errors import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter()


def _build_out(req) -> LeaveRequestOut:
    """Convert a LeaveRequest ORM instance to the enriched response schema."""
    employee_name = "Unknown"
    employee_avatar_url = None
    if hasattr(req, "employee") and req.employee:
        emp = req.employee
        employee_name = emp.full_name if hasattr(emp, "full_name") else f"#{emp.id}"
        employee_avatar_url = getattr(emp, "avatar_url", None)

    leave_type_name = "Unknown"
    leave_type_color = "#3b82f6"
    leave_type_is_paid = True
    if hasattr(req, "leave_type") and req.leave_type:
        lt = req.leave_type
        leave_type_name = lt.name
        leave_type_color = lt.color
        leave_type_is_paid = lt.is_paid

    department_name = None
    department_id = getattr(req, "department_id", None)
    if hasattr(req, "department") and req.department:
        department_name = req.department.name

    approver_name = None
    if hasattr(req, "approver") and req.approver:
        approver_name = req.approver.full_name if hasattr(req.approver, "full_name") else str(req.approver.id)

    return LeaveRequestOut(
        id=req.id,
        employee_id=req.employee_id,
        employee_name=employee_name,
        employee_avatar_url=employee_avatar_url,
        leave_type_id=req.leave_type_id,
        leave_type_name=leave_type_name,
        leave_type_color=leave_type_color,
        leave_type_is_paid=leave_type_is_paid,
        department_id=department_id,
        department_name=department_name,
        start_date=req.start_date,
        end_date=req.end_date,
        days_requested=float(req.days_requested),
        status=req.status,
        reason=req.reason,
        approved_by=req.approved_by,
        approver_name=approver_name,
        manager_note=req.manager_note,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


# ── helpers ──────────────────────────────────────────────────────────────────


async def _get_employee_id_for_user(db: AsyncSession, user: User) -> int:
    """Resolve the Employee.id for a given User."""
    result = await db.execute(
        select(Employee).where(Employee.user_id == user.id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise PermissionDeniedError("No employee profile found for your account")
    return emp.id


# ── public endpoints ────────────────────────────────────────────────────────


@router.get("/", response_model=PaginatedLeaveResponse)
async def api_list_leave_requests(
    params: LeaveRequestListParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List leave requests (authenticated).

    Admins/Managers see all requests. Employees see only their own.
    """
    skip = (params.page - 1) * params.page_size
    emp_id: int | None = None

    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        items, total = await list_leave_requests(
            db,
            skip=skip,
            limit=params.page_size,
            status=params.status,
            leave_type_id=params.leave_type_id,
        )
    else:
        emp_id = await _get_employee_id_for_user(db, current_user)
        items, total = await list_leave_requests(
            db,
            skip=skip,
            limit=params.page_size,
            status=params.status,
            employee_id=emp_id,
        )

    total_pages = math.ceil(total / params.page_size) if total > 0 else 1
    return PaginatedLeaveResponse(
        items=[_build_out(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


# ── employee endpoints ──────────────────────────────────────────────────────


@router.post("/", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
async def api_create_leave_request(
    data: LeaveRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new leave request (authenticated user)."""
    emp_id = await _get_employee_id_for_user(db, current_user)

    # Get employee record for status + department check
    result = await db.execute(
        select(Employee).where(Employee.id == emp_id)
    )
    employee = result.scalar_one_or_none()
    if employee and employee.status != "active":
        raise PermissionDeniedError("Only active employees can submit leave requests")

    if data.start_date > data.end_date:
        raise ValidationError("start_date must be before end_date")

    req = await create_leave_request(
        db, data, employee_id=emp_id, department_id=employee.department_id if employee else None
    )
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_request.created",
        entity="leave_request",
        entity_id=req.id,
        changes={"new": data.model_dump(mode="json")},
    )

    if employee:
        await notify_leave_requested(db, req, employee)

    return _build_out(req)


@router.get("/{request_id}", response_model=LeaveRequestOut)
async def api_get_leave_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single leave request."""
    req = await get_leave_request(db, request_id)
    if not req:
        raise NotFoundError("Leave request not found")

    # Employees can only see their own requests; managers/admins can see all
    if current_user.role == UserRole.EMPLOYEE:
        my_emp_id = await _get_employee_id_for_user(db, current_user)
        if req.employee_id != my_emp_id:
            raise PermissionDeniedError("You can only view your own leave requests")

    return _build_out(req)


# ── manager/admin endpoints ─────────────────────────────────────────────────


@router.put("/{request_id}/approve", response_model=LeaveRequestOut)
async def api_approve_leave_request(
    request_id: int,
    data: LeaveRequestUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Approve a leave request (manager or admin)."""
    req = await get_leave_request(db, request_id)
    if not req:
        raise NotFoundError("Leave request not found")

    old_status = req.status
    req = await approve_leave_request(db, req, data, approver_id=current_user.id)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_request.approved",
        entity="leave_request",
        entity_id=req.id,
        changes={"old": {"status": old_status}, "new": {"status": req.status}},
    )

    await notify_leave_decided(db, req)

    return _build_out(req)


@router.put("/{request_id}/reject", response_model=LeaveRequestOut)
async def api_reject_leave_request(
    request_id: int,
    data: LeaveRequestUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Reject a leave request (manager or admin)."""
    req = await get_leave_request(db, request_id)
    if not req:
        raise NotFoundError("Leave request not found")

    old_status = req.status
    req = await reject_leave_request(db, req, data)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_request.rejected",
        entity="leave_request",
        entity_id=req.id,
        changes={"old": {"status": old_status}, "new": {"status": req.status}},
    )

    await notify_leave_decided(db, req)

    return _build_out(req)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_cancel_leave_request(
    request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel (delete) a leave request. Employees can cancel their own; admins can cancel any."""
    req = await get_leave_request(db, request_id)
    if not req:
        raise NotFoundError("Leave request not found")

    if current_user.role == UserRole.EMPLOYEE:
        emp_id = await _get_employee_id_for_user(db, current_user)
        if req.employee_id != emp_id:
            raise PermissionDeniedError("You can only cancel your own leave requests")

    snapshot = {"status": req.status, "employee_id": req.employee_id}
    await cancel_leave_request(db, req)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="leave_request.cancelled",
        entity="leave_request",
        entity_id=request_id,
        changes={"old": snapshot},
    )
    return None