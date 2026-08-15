import api from "./api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface PayrollRunOut {
  id: number;
  period_start: string;
  period_end: string;
  status: "draft" | "processed" | "paid";
  notes: string | null;
  generated_at: string | null;
  total_gross: number;
  total_net: number;
  entry_count: number;
  created_at: string;
  updated_at: string;
}

export interface PayrollRunCreate {
  period_start: string;
  period_end: string;
  notes?: string;
}

export interface PayrollRunUpdate {
  period_start?: string;
  period_end?: string;
  status?: "draft" | "processed" | "paid";
  notes?: string;
}

export interface PayrollEntryOut {
  id: number;
  payroll_run_id: number;
  employee_id: number;
  employee_name: string;
  gross_salary: number;
  bonuses: number;
  deductions: number;
  net_pay: number;
  notes: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type PaginatedPayrollRunResponse = PaginatedResponse<PayrollRunOut>;
export type PaginatedPayrollEntryResponse = PaginatedResponse<PayrollEntryOut>;

export interface DeductionRuleOut {
  id: number;
  name: string;
  description: string | null;
  deduction_type: "fixed" | "percentage";
  value: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeductionRuleCreate {
  name: string;
  description?: string;
  deduction_type?: "fixed" | "percentage";
  value: number;
  active?: boolean;
}

export interface DeductionRuleUpdate {
  name?: string;
  description?: string;
  deduction_type?: "fixed" | "percentage";
  value?: number;
  active?: boolean;
}

export type PaginatedDeductionRuleResponse = PaginatedResponse<DeductionRuleOut>;

// ── Payroll Runs ──────────────────────────────────────────────────────────────

export async function listPayrollRuns(
  params?: { page?: number; page_size?: number; status?: string; search?: string }
): Promise<PaginatedPayrollRunResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.status) qs.set("status", params.status);
  if (params?.search) qs.set("search", params.search);
  const { data } = await api.get(`/payroll-runs?${qs}`);
  return data;
}

export async function getPayrollRun(id: number): Promise<PayrollRunOut> {
  const { data } = await api.get(`/payroll-runs/${id}`);
  return data;
}

export async function createPayrollRun(payload: PayrollRunCreate): Promise<PayrollRunOut> {
  const { data } = await api.post("/payroll-runs", payload);
  return data;
}

export async function updatePayrollRun(id: number, payload: PayrollRunUpdate): Promise<PayrollRunOut> {
  const { data } = await api.put(`/payroll-runs/${id}`, payload);
  return data;
}

export async function processPayrollRun(id: number): Promise<PayrollRunOut> {
  const { data } = await api.post(`/payroll-runs/${id}/process`);
  return data;
}

export async function calculatePayrollRun(id: number): Promise<PayrollRunOut> {
  const { data } = await api.post(`/payroll-runs/${id}/calculate`);
  return data;
}

export async function deletePayrollRun(id: number): Promise<void> {
  await api.delete(`/payroll-runs/${id}`);
}

// ── Payroll Entries ────────────────────────────────────────────────────────────

export async function listPayrollEntries(
  runId: number,
  params?: { page?: number; page_size?: number }
): Promise<PaginatedPayrollEntryResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const { data } = await api.get(`/payroll-runs/${runId}/entries?${qs}`);
  return data;
}

// ── Deduction Rules ────────────────────────────────────────────────────────────

export async function listDeductionRules(
  params?: { page?: number; page_size?: number; active_only?: boolean; search?: string }
): Promise<PaginatedDeductionRuleResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.active_only !== undefined) qs.set("active_only", String(params.active_only));
  if (params?.search) qs.set("search", params.search);
  const { data } = await api.get(`/deduction-rules?${qs}`);
  return data;
}

export async function getDeductionRule(id: number): Promise<DeductionRuleOut> {
  const { data } = await api.get(`/deduction-rules/${id}`);
  return data;
}

export async function createDeductionRule(payload: DeductionRuleCreate): Promise<DeductionRuleOut> {
  const { data } = await api.post("/deduction-rules", payload);
  return data;
}

export async function updateDeductionRule(id: number, payload: DeductionRuleUpdate): Promise<DeductionRuleOut> {
  const { data } = await api.put(`/deduction-rules/${id}`, payload);
  return data;
}

export async function deleteDeductionRule(id: number): Promise<void> {
  await api.delete(`/deduction-rules/${id}`);
}