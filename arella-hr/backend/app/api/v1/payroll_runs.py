"""Payroll run API endpoints."""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import payroll_run as crud
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.payroll_run import (
    PaginatedPayrollEntryResponse,
    PaginatedPayrollRunResponse,
    PayrollEntryOut,
    PayrollRunCreate,
    PayrollRunListParams,
    PayrollRunOut,
    PayrollRunUpdate,
)
from app.services.audit import diff_changes, record_audit
from app.services.email import notify_payroll_processed
from app.services.notifications import (
    notify_payroll_processed as notify_payroll_processed_inapp,
)
from app.utils.errors import NotFoundError, ValidationError

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────


def _build_run_out(payroll_run):
    """Convert a PayrollRun ORM instance to the response schema."""
    total_gross = sum(float(e.gross_salary) for e in payroll_run.entries)
    total_net = sum(float(e.net_pay) for e in payroll_run.entries)
    return PayrollRunOut(
        id=payroll_run.id,
        period_start=payroll_run.period_start,
        period_end=payroll_run.period_end,
        status=payroll_run.status,
        notes=payroll_run.notes,
        generated_at=payroll_run.generated_at,
        total_gross=round(total_gross, 2),
        total_net=round(total_net, 2),
        entry_count=len(payroll_run.entries),
        created_at=payroll_run.created_at,
        updated_at=payroll_run.updated_at,
    )


def _build_entry_out(entry, employee_name: str):
    """Convert a PayrollEntry ORM instance to the response schema."""
    return PayrollEntryOut(
        id=entry.id,
        payroll_run_id=entry.payroll_run_id,
        employee_id=entry.employee_id,
        employee_name=employee_name,
        gross_salary=float(entry.gross_salary),
        bonuses=float(entry.bonuses),
        deductions=float(entry.deductions),
        net_pay=float(entry.net_pay),
        notes=entry.notes,
        created_at=entry.created_at,
    )


async def _resolve_employee_name(db: AsyncSession, emp_id: int) -> str:
    """Resolve an employee's display name by ID."""
    result = await db.execute(select(Employee).where(Employee.id == emp_id))
    emp = result.scalar_one_or_none()
    if emp and hasattr(emp, "full_name"):
        return emp.full_name
    return f"Employee #{emp_id}"


# ── list ─────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedPayrollRunResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_list_payroll_runs(
    params: PayrollRunListParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of payroll runs."""
    items, total = await crud.list_payroll_runs(
        db,
        page=params.page,
        page_size=params.page_size,
        status=params.status,
        search=params.search,
    )
    total_pages = math.ceil(total / params.page_size) if total else 0

    return PaginatedPayrollRunResponse(
        items=[_build_run_out(r) for r in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


# ── detail ───────────────────────────────────────────────────────────────────


@router.get(
    "/{run_id}",
    response_model=PayrollRunOut,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_get_payroll_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a single payroll run by ID."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")
    return _build_run_out(payroll_run)


# ── entries ──────────────────────────────────────────────────────────────────


@router.get(
    "/{run_id}/entries",
    response_model=PaginatedPayrollEntryResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_list_payroll_entries(
    run_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated entries for a payroll run."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")

    items, total = await crud.list_payroll_entries(
        db, run_id, page=page, page_size=page_size
    )
    total_pages = math.ceil(total / page_size) if total else 0

    entries_out = []
    for entry in items:
        emp_name = await _resolve_employee_name(db, entry.employee_id)
        entries_out.append(_build_entry_out(entry, emp_name))

    return PaginatedPayrollEntryResponse(
        items=entries_out,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        run_id=run_id,
    )


# ── create ───────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PayrollRunOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_create_payroll_run(
    payload: PayrollRunCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payroll run in draft status."""
    if payload.period_end < payload.period_start:
        raise ValidationError("period_end must be after period_start")

    payroll_run = await crud.create_payroll_run(
        db,
        period_start=payload.period_start,
        period_end=payload.period_end,
        notes=payload.notes,
    )
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="payroll_run.created",
        entity="payroll_run",
        entity_id=payroll_run.id,
        changes={"new": payload.model_dump(mode="json")},
    )
    return _build_run_out(payroll_run)


# ── update ───────────────────────────────────────────────────────────────────


@router.put(
    "/{run_id}",
    response_model=PayrollRunOut,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_update_payroll_run(
    run_id: int,
    payload: PayrollRunUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a payroll run."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")

    update_kwargs = {
        k: v for k, v in {
            "period_start": payload.period_start,
            "period_end": payload.period_end,
            "status": payload.status,
            "notes": payload.notes,
        }.items()
        if v is not None
    }
    old_snapshot = {k: getattr(payroll_run, k, None) for k in update_kwargs}
    changes = diff_changes(old_snapshot, update_kwargs)
    updated = await crud.update_payroll_run(db, payroll_run, **update_kwargs)
    if changes is not None:
        await record_audit(
            db,
            user=current_user,
            request=request,
            action="payroll_run.updated",
            entity="payroll_run",
            entity_id=updated.id,
            changes=changes,
        )
    return _build_run_out(updated)


# ── process payroll ─────────────────────────────────────────────────────────


@router.post(
    "/{run_id}/process",
    response_model=PayrollRunOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_process_payroll_run(
    run_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate and process a payroll run (generate entries for all employees)."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")

    if payroll_run.status != "draft":
        raise ValidationError("Only draft payroll runs can be processed")

    # Import the service here
    from app.services.payroll import calculate_payroll_for_run, calculate_run_totals

    try:
        entries = await calculate_payroll_for_run(db, payroll_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payroll calculation failed: {str(e)}")

    # Update run status
    payroll_run.status = "processed"
    payroll_run.generated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payroll_run)

    await record_audit(
        db,
        user=current_user,
        request=request,
        action="payroll_run.processed",
        entity="payroll_run",
        entity_id=payroll_run.id,
        changes={"new": {"status": "processed"}},
    )
    await notify_payroll_processed(db, payroll_run, entries)
    await notify_payroll_processed_inapp(db, payroll_run, entries)
    return _build_run_out(payroll_run)


# ── delete ───────────────────────────────────────────────────────────────────


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_delete_payroll_run(
    run_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a draft payroll run."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")

    snapshot = {"period_start": str(payroll_run.period_start), "period_end": str(payroll_run.period_end)}
    await crud.delete_payroll_run(db, payroll_run)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="payroll_run.deleted",
        entity="payroll_run",
        entity_id=run_id,
        changes={"old": snapshot},
    )
    return None


# ── calculate preview ───────────────────────────────────────────────────────


@router.post(
    "/{run_id}/calculate",
    response_model=PayrollRunOut,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_calculate_payroll_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Recalculate entries for a payroll run (useful after changing deduction rules)."""
    payroll_run = await crud.get_payroll_run(db, run_id)
    if not payroll_run:
        raise NotFoundError("Payroll run not found")

    from app.services.payroll import regenerate_entries

    try:
        await regenerate_entries(db, payroll_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payroll recalculation failed: {str(e)}")

    return _build_run_out(payroll_run)