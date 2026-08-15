import api from "./api";

// ── Type definitions ─────────────────────────────────────────────────────────

export interface Department {
  id: number;
  name: string;
  description: string | null;
  manager_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveType {
  id: number;
  name: string;
  description: string | null;
  days_per_year: number;
  max_consecutive_days: number;
  is_paid: boolean;
  color: string;
  requires_approval: boolean;
  active: boolean;
  created_at: string;
}

export interface LeaveBalance {
  id: number;
  employee_id: number;
  leave_type_id: number;
  leave_type_name: string;
  year: number;
  allocated: number;
  used: number;
  carried_over: number;
  remaining: number;
  utilization_pct: number;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_avatar_url: string | null;
  leave_type_id: number;
  leave_type_name: string;
  leave_type_color: string;
  leave_type_is_paid: boolean;
  department_id: number | null;
  department_name: string | null;
  start_date: string;
  end_date: string;
  days_requested: number;
  status: "pending" | "approved" | "rejected";
  reason: string | null;
  approved_by: number | null;
  approver_name: string | null;
  manager_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestCreate {
  leave_type_id: number;
  start_date: string;
  end_date: string;
  reason?: string;
}

export interface LeaveRequestUpdate {
  status: "approved" | "rejected";
  manager_note?: string;
}

export interface PaginatedLeaveResponse {
  items: LeaveRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Department API ───────────────────────────────────────────────────────────

export function listDepartments(skip = 0, limit = 100) {
  return api.get<Department[]>("/departments/", { params: { skip, limit } }).then((r) => r.data);
}

export function getDepartment(id: number) {
  return api.get<Department>(`/departments/${id}`).then((r) => r.data);
}

export function createDepartment(data: { name: string; description?: string; manager_id?: number }) {
  return api.post<Department>("/departments/", data).then((r) => r.data);
}

export function updateDepartment(id: number, data: { name?: string; description?: string; manager_id?: number }) {
  return api.put<Department>(`/departments/${id}`, data).then((r) => r.data);
}

// ── Leave Type API ───────────────────────────────────────────────────────────

export function listLeaveTypes(activeOnly = true) {
  return api.get<LeaveType[]>("/leave-types/", { params: { active_only: activeOnly } }).then((r) => r.data);
}

export function getLeaveType(id: number) {
  return api.get<LeaveType>(`/leave-types/${id}`).then((r) => r.data);
}

export function createLeaveType(data: {
  name: string;
  description?: string;
  days_per_year?: number;
  max_consecutive_days?: number;
  is_paid?: boolean;
  color?: string;
  requires_approval?: boolean;
  active?: boolean;
}) {
  return api.post<LeaveType>("/leave-types/", data).then((r) => r.data);
}

export function updateLeaveType(
  id: number,
  data: {
    name?: string;
    description?: string;
    days_per_year?: number;
    max_consecutive_days?: number;
    is_paid?: boolean;
    color?: string;
    requires_approval?: boolean;
    active?: boolean;
  }
) {
  return api.put<LeaveType>(`/leave-types/${id}`, data).then((r) => r.data);
}

// ── Leave Balance API ────────────────────────────────────────────────────────

export function listLeaveBalances(employeeId?: number, year?: number) {
  return api.get<LeaveBalance[]>("/leave-balances/", { params: { employee_id: employeeId, year } }).then((r) => r.data);
}

export function createLeaveBalance(data: {
  employee_id: number;
  leave_type_id: number;
  year: number;
  allocated: number;
  carried_over?: number;
}) {
  return api.post<LeaveBalance>("/leave-balances/", data).then((r) => r.data);
}

// ── Leave Request API ────────────────────────────────────────────────────────

export function listLeaveRequests(
  page = 1,
  pageSize = 20,
  status?: string,
  leaveTypeId?: number
) {
  return api
    .get<PaginatedLeaveResponse>("/leave-requests/", {
      params: { page, page_size: pageSize, status, leave_type_id: leaveTypeId },
    })
    .then((r) => r.data);
}

export function getLeaveRequest(id: number) {
  return api.get<LeaveRequest>(`/leave-requests/${id}`).then((r) => r.data);
}

export function createLeaveRequest(data: LeaveRequestCreate) {
  return api.post<LeaveRequest>("/leave-requests/", data).then((r) => r.data);
}

export function approveLeaveRequest(id: number, data: { manager_note?: string }) {
  return api.put<LeaveRequest>(`/leave-requests/${id}/approve`, { status: "approved", ...data }).then((r) => r.data);
}

export function rejectLeaveRequest(id: number, data: { manager_note: string }) {
  return api.put<LeaveRequest>(`/leave-requests/${id}/reject`, { status: "rejected", ...data }).then((r) => r.data);
}

export function cancelLeaveRequest(id: number) {
  return api.delete<void>(`/leave-requests/${id}`).then((r) => r.data);
}