import api from "./api";

// ── Type definitions ─────────────────────────────────────────────────────────

export interface ReviewCycle {
  id: number;
  name: string;
  period_start: string;
  period_end: string;
  status: "active" | "closed";
  description: string | null;
  created_at: string;
  total_reviews: number;
  drafts: number;
  submitted: number;
  shared: number;
}

export interface ReviewCycleCreate {
  name: string;
  period_start: string;
  period_end: string;
  description?: string;
}

export interface Review {
  id: number;
  cycle_id: number;
  cycle_name: string;
  cycle_status: string;
  employee_id: number;
  employee_name: string;
  employee_position: string | null;
  employee_department: string | null;
  reviewer_user_id: number | null;
  reviewer_name: string | null;
  rating: number | null;
  strengths: string | null;
  improvements: string | null;
  goals: string | null;
  status: "draft" | "submitted" | "shared";
  submitted_at: string | null;
  shared_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCreate {
  employee_id: number;
  rating?: number | null;
  strengths?: string | null;
  improvements?: string | null;
  goals?: string | null;
  /** False = save as draft, True = submit for sharing. */
  submit: boolean;
}

export interface ReviewUpdate {
  rating?: number | null;
  strengths?: string | null;
  improvements?: string | null;
  goals?: string | null;
  status?: "draft" | "submitted";
}

// ── API ──────────────────────────────────────────────────────────────────────

export function listReviewCycles() {
  return api.get<ReviewCycle[]>("/review-cycles/").then((r) => r.data);
}

export function createReviewCycle(data: ReviewCycleCreate) {
  return api.post<ReviewCycle>("/review-cycles/", data).then((r) => r.data);
}

export function listCycleReviews(cycleId: number) {
  return api.get<Review[]>(`/review-cycles/${cycleId}/reviews/`).then((r) => r.data);
}

export function getReview(id: number) {
  return api.get<Review>(`/reviews/${id}`).then((r) => r.data);
}

export function createReview(cycleId: number, data: ReviewCreate) {
  return api.post<Review>(`/review-cycles/${cycleId}/reviews/`, data).then((r) => r.data);
}

export function updateReview(id: number, data: ReviewUpdate) {
  return api.patch<Review>(`/reviews/${id}`, data).then((r) => r.data);
}

export function shareReview(id: number) {
  return api.post<Review>(`/reviews/${id}/share`).then((r) => r.data);
}
