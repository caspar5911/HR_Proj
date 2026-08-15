import api from "./api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface AuditLogOut {
  id: number;
  user_id: number | null;
  user_email: string | null;
  action: string;
  entity: string;
  entity_id: number | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  timestamp: string;
}

export interface PaginatedAuditLogResponse {
  items: AuditLogOut[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditLogListParams {
  page?: number;
  page_size?: number;
  user_id?: number;
  entity?: string;
  action?: string;
  entity_id?: number;
  start?: string;
  end?: string;
}

// ── API (admin-only endpoints) ────────────────────────────────────────────────

export async function listAuditLogs(
  params: AuditLogListParams = {}
): Promise<PaginatedAuditLogResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  if (params.user_id) qs.set("user_id", String(params.user_id));
  if (params.entity) qs.set("entity", params.entity);
  if (params.action) qs.set("action", params.action);
  if (params.entity_id) qs.set("entity_id", String(params.entity_id));
  if (params.start) qs.set("start", params.start);
  if (params.end) qs.set("end", params.end);
  const { data } = await api.get(`/audit-logs?${qs}`);
  return data;
}
