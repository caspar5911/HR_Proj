import api from "./api";

// ── Type definitions ─────────────────────────────────────────────────────────

export type GoalStatus = "active" | "completed" | "archived";

export interface Goal {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_position: string | null;
  employee_department: string | null;
  title: string;
  description: string | null;
  period: string;
  progress: number;
  status: GoalStatus;
  completed_at: string | null;
  created_by_user_id: number | null;
  creator_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  employee_id: number;
  title: string;
  description?: string | null;
  period: string;
  progress?: number;
}

export interface GoalUpdate {
  title?: string;
  description?: string | null;
  progress?: number;
  status?: GoalStatus;
}

export interface GoalListParams {
  period?: string;
  status?: GoalStatus;
  employee_id?: number;
}

// ── API ──────────────────────────────────────────────────────────────────────

/**
 * Goals visible to the caller, scoped server-side by role:
 * admins see every goal, managers their own + direct reports', employees their own.
 */
export function listGoals(params: GoalListParams = {}) {
  return api.get<Goal[]>("/goals/", { params }).then((r) => r.data);
}

export function createGoal(data: GoalCreate) {
  return api.post<Goal>("/goals/", data).then((r) => r.data);
}

export function updateGoal(id: number, data: GoalUpdate) {
  return api.patch<Goal>(`/goals/${id}`, data).then((r) => r.data);
}

export function deleteGoal(id: number) {
  return api.delete(`/goals/${id}`);
}
