import api from "./api";
import type { AuditLogOut } from "./audit";

// ── Types (mirror backend/app/schemas/dashboard.py) ─────────────────────────

export interface StatusCount {
  status: string;
  count: number;
}

export interface DepartmentHeadcount {
  department: string;
  count: number;
  active: number;
}

/** Monthly new-hire count; `month` is "YYYY-MM". */
export interface HirePoint {
  month: string;
  hires: number;
}

export interface LeaveStatusCount {
  status: string;
  count: number;
}

export interface LeaveTypeCount {
  leave_type: string;
  color: string;
  count: number;
}

export interface LeaveUtilization {
  leave_type: string;
  color: string;
  allocated: number;
  used: number;
  remaining: number;
  utilization_pct: number;
}

export interface PayrollSnapshot {
  run_id: number | null;
  period_start: string | null;
  period_end: string | null;
  status: string | null;
  entry_count: number;
  total_gross: number;
  total_net: number;
  average_net: number;
}

export interface Kpis {
  total_employees: number;
  active_employees: number;
  on_leave: number;
  inactive: number;
  pending_leave: number;
  headcount_by_status: StatusCount[];
  avg_salary: number;
  latest_net_payroll: number;
}

/** Everything the dashboard page needs in one round-trip. */
export interface DashboardSummary {
  kpis: Kpis;
  headcount_by_department: DepartmentHeadcount[];
  hiring_trend: HirePoint[];
  leave_by_status: LeaveStatusCount[];
  leave_by_type: LeaveTypeCount[];
  leave_utilization: LeaveUtilization[];
  payroll_snapshot: PayrollSnapshot;
  recent_activity: AuditLogOut[];
}

/** One employee's leave block on the team absence calendar. */
export interface TeamDay {
  employee_id: number;
  employee_name: string;
  leave_type: string;
  color: string;
  status: string;
  start_date: string;
  end_date: string;
  days: number;
}

/** Approved + pending leave overlapping a month. Employees get their own. */
export interface TeamSchedule {
  year: number;
  month: number;
  days: TeamDay[];
}

// ── API ──────────────────────────────────────────────────────────────────────

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get("/dashboard/summary");
  return data;
}

export async function getTeamSchedule(year: number, month: number): Promise<TeamSchedule> {
  const { data } = await api.get("/dashboard/team-schedule", { params: { year, month } });
  return data;
}
