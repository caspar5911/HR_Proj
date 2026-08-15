"""Dashboard analytics schemas — aggregated views for the KPI/charts UI."""

from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.schemas.audit_log import AuditLogOut


class StatusCount(BaseModel):
    status: str
    count: int


class DepartmentHeadcount(BaseModel):
    department: str
    count: int
    active: int


class HirePoint(BaseModel):
    """Monthly new-hire count for the hiring-trend chart."""
    month: str  # "2026-08"
    hires: int


class LeaveStatusCount(BaseModel):
    status: str
    count: int


class LeaveTypeCount(BaseModel):
    leave_type: str
    color: str
    count: int


class LeaveUtilization(BaseModel):
    leave_type: str
    color: str
    allocated: float
    used: float
    remaining: float
    utilization_pct: float


class PayrollSnapshot(BaseModel):
    run_id: Optional[int]
    period_start: Optional[date]
    period_end: Optional[date]
    status: Optional[str]
    entry_count: int
    total_gross: float
    total_net: float
    average_net: float


class Kpis(BaseModel):
    total_employees: int
    active_employees: int
    on_leave: int
    inactive: int
    pending_leave: int
    headcount_by_status: list[StatusCount]
    avg_salary: float
    latest_net_payroll: float


class DashboardSummary(BaseModel):
    """Everything the dashboard page needs in a single round-trip."""

    kpis: Kpis
    headcount_by_department: list[DepartmentHeadcount]
    hiring_trend: list[HirePoint]
    leave_by_status: list[LeaveStatusCount]
    leave_by_type: list[LeaveTypeCount]
    leave_utilization: list[LeaveUtilization]
    payroll_snapshot: PayrollSnapshot
    recent_activity: list[AuditLogOut]


class TeamDay(BaseModel):
    """One employee's block on the team absence calendar."""
    employee_id: int
    employee_name: str
    leave_type: str
    color: str
    status: str
    start_date: date
    end_date: date
    days: float


class TeamSchedule(BaseModel):
    """Approved + pending leave for a month, for the team calendar view."""
    year: int
    month: int
    days: list[TeamDay]
