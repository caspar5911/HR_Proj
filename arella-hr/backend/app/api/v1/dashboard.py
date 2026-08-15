"""Dashboard analytics endpoints — KPIs, charts, and the team calendar.

Everything here is read-only and aggregated server-side so the UI makes a
single round-trip for the whole dashboard rather than stitching together
half a dozen paginated lists.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.payroll_entry import PayrollEntry
from app.models.payroll_run import PayrollRun
from app.models.user import UserRole
from app.schemas.audit_log import AuditLogOut
from app.schemas.dashboard import (
    DashboardSummary,
    DepartmentHeadcount,
    HirePoint,
    Kpis,
    LeaveStatusCount,
    LeaveTypeCount,
    LeaveUtilization,
    PayrollSnapshot,
    StatusCount,
    TeamDay,
    TeamSchedule,
)

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────


def _month_key(d: date) -> str:
    """'2026-08' style key for a date."""
    return d.strftime("%Y-%m")


def _last_n_months(n: int, ref: datetime) -> list[tuple[int, int]]:
    """Return the last ``n`` (year, month) pairs ending at ``ref``'s month,
    oldest first."""
    out: list[tuple[int, int]] = []
    y, m = ref.year, ref.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _audit_out(log: AuditLog) -> AuditLogOut:
    user_email = log.user.email if log.user is not None else None
    return AuditLogOut(
        id=log.id,
        user_id=log.user_id,
        user_email=user_email,
        action=log.action,
        entity=log.entity,
        entity_id=log.entity_id,
        changes=log.changes,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        timestamp=log.timestamp,
    )


# ── summary ─────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=DashboardSummary,
    # Org-wide KPIs (headcount, net payroll totals) are staff data —
    # plain employees land in self-service "My Home" instead.
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Aggregated dashboard payload in one call."""
    now = datetime.now(timezone.utc)
    current_year = now.year

    # ── employees ──
    employees = (await db.execute(select(Employee))).scalars().all()
    total_employees = len(employees)
    status_counts: dict[str, int] = {}
    dept_total: dict[str, int] = {}
    dept_active: dict[str, int] = {}
    hire_months: dict[str, int] = {}
    salaried = [e for e in employees if e.salary_base is not None]
    avg_salary = round(sum(float(e.salary_base) for e in salaried) / len(salaried), 2) if salaried else 0.0

    for e in employees:
        status_counts[e.status] = status_counts.get(e.status, 0) + 1
        name = e.department or "Unassigned"
        dept_total[name] = dept_total.get(name, 0) + 1
        if e.status == "active":
            dept_active[name] = dept_active.get(name, 0) + 1
        if e.hire_date is not None:
            key = _month_key(e.hire_date)
            hire_months[key] = hire_months.get(key, 0) + 1

    headcount_by_status = [
        StatusCount(status=s, count=c)
        for s, c in sorted(status_counts.items(), key=lambda kv: -kv[1])
    ]
    headcount_by_department = [
        DepartmentHeadcount(
            department=d,
            count=dept_total.get(d, 0),
            active=dept_active.get(d, 0),
        )
        for d in sorted(dept_total, key=lambda d: -dept_total[d])
    ]
    hiring_trend = [
        HirePoint(month=f"{y}-{m:02d}", hires=hire_months.get(f"{y}-{m:02d}", 0))
        for y, m in _last_n_months(12, now)
    ]

    # ── leave requests ──
    requests = (await db.execute(select(LeaveRequest))).scalars().all()
    leave_by_status: dict[str, int] = {}
    leave_by_type: dict[str, int] = {}
    for r in requests:
        leave_by_status[r.status] = leave_by_status.get(r.status, 0) + 1
        lt = r.leave_type
        name = lt.name if lt else "Unknown"
        leave_by_type[name] = leave_by_type.get(name, 0) + 1

    type_color: dict[str, str] = {
        t.name: t.color for t in (await db.execute(select(LeaveType))).scalars().all()
    }
    leave_by_type_out = [
        LeaveTypeCount(leave_type=n, color=type_color.get(n, "#3b82f6"), count=c)
        for n, c in sorted(leave_by_type.items(), key=lambda kv: -kv[1])
    ]
    leave_by_status_out = [
        LeaveStatusCount(status=s, count=c)
        for s, c in sorted(leave_by_status.items(), key=lambda kv: -kv[1])
    ]
    pending_leave = leave_by_status.get("pending", 0)

    # ── leave utilization (current year) ──
    balances = (
        await db.execute(
            select(LeaveBalance).where(LeaveBalance.year == current_year)
        )
    ).scalars().all()
    util_by_type: dict[str, dict] = {}
    for b in balances:
        name = b.leave_type.name if b.leave_type else "Unknown"
        slot = util_by_type.setdefault(name, {"allocated": 0.0, "used": 0.0, "color": "#3b82f6"})
        slot["allocated"] += float(b.allocated + b.carried_over)
        slot["used"] += float(b.used)
        if b.leave_type and b.leave_type.color:
            slot["color"] = b.leave_type.color
    leave_utilization = []
    for name, v in util_by_type.items():
        total = v["allocated"]
        remaining = max(0.0, total - v["used"])
        pct = round(min(100.0, (v["used"] / total) * 100), 1) if total > 0 else 0.0
        leave_utilization.append(
            LeaveUtilization(
                leave_type=name,
                color=v["color"],
                allocated=round(v["allocated"], 1),
                used=round(v["used"], 1),
                remaining=round(remaining, 1),
                utilization_pct=pct,
            )
        )
    leave_utilization.sort(key=lambda u: -u.utilization_pct)

    # ── payroll snapshot: prefer the latest processed/paid run (real numbers);
    # fall back to the most recent run (e.g. a draft) if none has processed yet ──
    latest_run = (
        await db.execute(
            select(PayrollRun)
            .where(PayrollRun.status.in_(["processed", "paid"]))
            .order_by(PayrollRun.period_start.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_run is None:
        latest_run = (
            await db.execute(
                select(PayrollRun).order_by(PayrollRun.period_start.desc()).limit(1)
            )
        ).scalar_one_or_none()
    if latest_run is not None:
        entries = (
            await db.execute(
                select(PayrollEntry).where(
                    PayrollEntry.payroll_run_id == latest_run.id
                )
            )
        ).scalars().all()
        total_gross = round(sum(float(e.gross_salary) + float(e.bonuses) for e in entries), 2)
        total_net = round(sum(float(e.net_pay) for e in entries), 2)
        avg_net = round(total_net / len(entries), 2) if entries else 0.0
        payroll_snapshot = PayrollSnapshot(
            run_id=latest_run.id,
            period_start=latest_run.period_start,
            period_end=latest_run.period_end,
            status=latest_run.status,
            entry_count=len(entries),
            total_gross=total_gross,
            total_net=total_net,
            average_net=avg_net,
        )
        latest_net = total_net
    else:
        payroll_snapshot = PayrollSnapshot(
            run_id=None, period_start=None, period_end=None, status=None,
            entry_count=0, total_gross=0.0, total_net=0.0, average_net=0.0,
        )
        latest_net = 0.0

    # ── recent activity ──
    recent = (
        await db.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(12)
        )
    ).scalars().all()
    recent_activity = [_audit_out(a) for a in recent]

    kpis = Kpis(
        total_employees=total_employees,
        active_employees=status_counts.get("active", 0),
        on_leave=status_counts.get("on_leave", 0),
        inactive=status_counts.get("inactive", 0),
        pending_leave=pending_leave,
        headcount_by_status=headcount_by_status,
        avg_salary=avg_salary,
        latest_net_payroll=latest_net,
    )

    return DashboardSummary(
        kpis=kpis,
        headcount_by_department=headcount_by_department,
        hiring_trend=hiring_trend,
        leave_by_status=leave_by_status_out,
        leave_by_type=leave_by_type_out,
        leave_utilization=leave_utilization,
        payroll_snapshot=payroll_snapshot,
        recent_activity=recent_activity,
    )


# ── team absence calendar ───────────────────────────────────────────────────


@router.get(
    "/team-schedule",
    response_model=TeamSchedule,
    # Team-wide absence calendar is staff-only; employees see their own
    # requests on the Leave page instead.
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def api_team_schedule(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """Approved + pending leave overlapping the given month, for the calendar."""
    start = date(year, month, 1)
    end = date(year, month, 1)
    # month end via next month start - 1 day
    if month == 12:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, month + 1, 1)
    month_end = next_start.fromordinal(next_start.toordinal() - 1)

    q = select(LeaveRequest).where(
        LeaveRequest.start_date <= month_end,
        LeaveRequest.end_date >= start,
        LeaveRequest.status.in_(["pending", "approved"]),
    )
    requests = (await db.execute(q)).scalars().all()
    days = [
        TeamDay(
            employee_id=r.employee_id,
            employee_name=r.employee.full_name if r.employee else "Unknown",
            leave_type=r.leave_type.name if r.leave_type else "Unknown",
            color=r.leave_type.color if r.leave_type and r.leave_type.color else "#3b82f6",
            status=r.status,
            start_date=r.start_date,
            end_date=r.end_date,
            days=float(r.days_requested),
        )
        for r in requests
    ]
    return TeamSchedule(year=year, month=month, days=days)
