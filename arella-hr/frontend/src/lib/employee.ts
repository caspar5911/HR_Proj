import api from "./api";

export interface Employee {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  department: string | null;
  position: string | null;
  hire_date: string | null;
  salary_base: number | null;
  address: string | null;
  manager_id: number | null;
  manager_name: string | null;
  status: "active" | "inactive" | "on_leave";
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreate {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  department?: string;
  position?: string;
  hire_date?: string;
  salary_base?: number;
  address?: string;
  manager_id?: number;
  status?: "active" | "inactive" | "on_leave";
  avatar_url?: string;
}

export interface EmployeeUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  department?: string;
  position?: string;
  hire_date?: string;
  salary_base?: number;
  address?: string;
  manager_id?: number;
  status?: "active" | "inactive" | "on_leave";
  avatar_url?: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EmployeeListParams {
  page?: number;
  page_size?: number;
  search?: string;
  department?: string;
  status?: string;
  position?: string;
  include_inactive?: boolean;
}

export function listEmployees(params: EmployeeListParams = {}) {
  return api.get<EmployeeListResponse>("/employees", { params });
}

export function getEmployee(id: number) {
  return api.get<Employee>(`/employees/${id}`);
}

export function createEmployee(data: EmployeeCreate) {
  return api.post<Employee>("/employees", data);
}

export function updateEmployee(id: number, data: EmployeeUpdate) {
  return api.put<Employee>(`/employees/${id}`, data);
}

export function deactivateEmployee(id: number) {
  return api.patch<Employee>(`/employees/${id}/deactivate`);
}

export function restoreEmployee(id: number) {
  return api.patch<Employee>(`/employees/${id}/restore`);
}

export function deleteEmployee(id: number) {
  return api.delete(`/employees/${id}`);
}

/** Recursive org tree node (top-level employees + nested direct reports). */
export interface OrgNode extends Employee {
  manager?: OrgNode | null;
  reports: OrgNode[];
}

export function getOrgTree() {
  return api.get<OrgNode[]>("/employees/org-tree");
}

/**
 * A single payslip: a payroll entry enriched with its run's period and the
 * employee's identifying details (printable stub).
 */
export interface Payslip {
  entry_id: number;
  run_id: number;
  period_start: string;
  period_end: string;
  run_status: string;
  employee_id: number;
  employee_name: string;
  position: string | null;
  department: string | null;
  gross_salary: number;
  bonuses: number;
  deductions: number;
  net_pay: number;
  notes: string | null;
  generated_at: string | null;
}

/**
 * The employee record linked to the signed-in user (404 when unlinked).
 * Powers the employee self-service "My Home" page.
 */
export function getMyProfile() {
  return api.get<Employee>("/employees/me").then((r) => r.data);
}

/** An employee's pay history as payslips, newest period first. */
export function getPayslips(employeeId: number) {
  return api.get<Payslip[]>(`/employees/${employeeId}/payslips`).then((r) => r.data);
}