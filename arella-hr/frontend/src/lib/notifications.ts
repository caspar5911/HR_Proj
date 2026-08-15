import api from "./api";

// ── Type definitions ─────────────────────────────────────────────────────────

export interface Notification {
  id: number;
  /** Free-form event type: "leave_requested" | "leave_approved" | … */
  type: string;
  title: string;
  body: string;
  /** In-app route to open (e.g. "/leave"), or null for plain announcements. */
  link: string | null;
  read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface PaginatedNotificationResponse {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── API ──────────────────────────────────────────────────────────────────────

export function listNotifications(page = 1, pageSize = 20) {
  return api
    .get<PaginatedNotificationResponse>("/notifications/", {
      params: { page, page_size: pageSize },
    })
    .then((r) => r.data);
}

export function getUnreadCount() {
  return api.get<{ unread: number }>("/notifications/unread-count").then((r) => r.data);
}

export function markNotificationRead(id: number) {
  return api.patch<Notification>(`/notifications/${id}/read`).then((r) => r.data);
}

export function markAllNotificationsRead() {
  return api.post<{ unread: number }>("/notifications/read-all").then((r) => r.data);
}
