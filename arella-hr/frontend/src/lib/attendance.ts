import api from "./api";

/** A recorded work day (clock in/out + breaks + worked hours). */
export interface TimeEntry {
  id: number;
  employee_id: number;
  employee_name: string;
  work_date: string;
  clock_in: string;
  clock_out: string | null;
  breaks_minutes: number;
  notes: string | null;
  /** Worked hours for the day, null while the day is still open. */
  hours: number | null;
  created_at: string;
  updated_at: string;
}

/** Clock in/out payload — one row per employee per day (upsert). */
export interface TimeEntryCreate {
  work_date: string;
  clock_in: string;
  clock_out?: string | null;
  breaks_minutes?: number;
  notes?: string | null;
}

/** One employee's entries for a month plus the month totals. */
export interface MonthAttendance {
  items: TimeEntry[];
  total_hours: number;
  days_recorded: number;
  avg_daily_hours: number | null;
}

/** Per-employee summary row for the manager attendance view. */
export interface TeamAttendanceRow {
  employee_id: number;
  employee_name: string;
  position: string | null;
  department: string | null;
  days_recorded: number;
  total_hours: number;
  avg_daily_hours: number | null;
  /** Hours beyond 8/day, summed for the month. */
  overtime_hours: number;
}

export interface MonthParams {
  year?: number;
  month?: number;
}

/** The signed-in user's time entries for a month (default: current). */
export function getMyMonthAttendance(params: MonthParams = {}) {
  return api.get<MonthAttendance>("/attendance/me", { params }).then((r) => r.data);
}

/** Clock in / clock out / update today's entry (one row per day). */
export function recordTime(data: TimeEntryCreate) {
  return api.post<TimeEntry>("/attendance/me", data).then((r) => r.data);
}

/** Per-employee attendance summary for a month (manager/admin). */
export function getTeamAttendance(params: MonthParams = {}) {
  return api.get<TeamAttendanceRow[]>("/attendance/team", { params }).then((r) => r.data);
}

/** One employee's time entries for a month (manager/admin). */
export function getEmployeeMonthAttendance(employeeId: number, params: MonthParams = {}) {
  return api.get<MonthAttendance>(`/attendance/employee/${employeeId}`, { params }).then((r) => r.data);
}

/** Local wall-clock "HH:MM:SS" for the current moment (no timezone math). */
export function nowClockTime(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** Local wall-clock "YYYY-MM-DD" for a date. */
export function toDateInput(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Format a "HH:MM:SS" wall-clock string as "h:mm AM/PM". */
export function formatClock(t: string | null): string {
  if (!t) return "—";
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}:${String(m).padStart(2, "0")} ${ampm}`;
}

/** Format a "YYYY-MM-DD" date as e.g. "Fri, Aug 15". */
export function formatWorkDate(d: string): string {
  return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}
