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

export function getOrgTree() {
  return api.get<Employee[]>("/employees/org-tree");
}