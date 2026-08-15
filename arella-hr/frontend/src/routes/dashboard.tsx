import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  DollarSign,
  Percent,
  TrendingUp,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import {
  getDashboardSummary,
  getTeamSchedule,
  type TeamDay,
} from "@/lib/dashboard";
import type { AuditLogOut } from "@/lib/audit";
import { useAuth } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatMoney(v: number, decimals = 0): string {
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  });
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function timeAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Human-readable one-liner for an audit log entry. */
function describeActivity(log: AuditLogOut): string {
  const who = log.user_email ?? "System";
  const c = (log.changes ?? {}) as Record<string, unknown>;
  const nw = (c.new ?? {}) as Record<string, unknown>;
  const name = typeof nw.name === "string" ? nw.name : null;
  let verb: string;
  switch (log.action) {
    case "login":
      verb = "signed in";
      break;
    case "employee.created":
      verb = `added ${name ?? "a new employee"}`;
      break;
    case "employee.updated":
      verb = "updated an employee record";
      break;
    case "employee.deactivated":
      verb = "deactivated an employee";
      break;
    case "employee.restored":
      verb = "restored an employee";
      break;
    case "employee.deleted":
      verb = "removed an employee";
      break;
    case "leave_request.created":
      verb = "submitted a leave request";
      break;
    case "leave_request.approved":
      verb = "approved a leave request";
      break;
    case "leave_request.rejected":
      verb = "rejected a leave request";
      break;
    case "leave_request.cancelled":
      verb = "canceled a leave request";
      break;
    case "payroll_run.created":
      verb = "created a payroll run";
      break;
    case "payroll_run.processed":
      verb = `processed payroll${typeof nw.entries === "number" ? ` (${nw.entries} entries)` : ""}`;
      break;
    case "payroll_run.updated":
      verb = "updated a payroll run";
      break;
    case "payroll_run.deleted":
      verb = "deleted a payroll run";
      break;
    case "deduction_rule.created":
      verb = `added the deduction rule “${name ?? "new"}”`;
      break;
    case "deduction_rule.updated":
      verb = "updated a deduction rule";
      break;
    case "deduction_rule.deleted":
      verb = "removed a deduction rule";
      break;
    case "department.created":
      verb = `created the department “${name ?? "new"}”`;
      break;
    default:
      verb = log.action.replace(/_/g, " ");
  }
  return `${who} ${verb}`;
}

const ENTITY_ICONS: Record<string, LucideIcon> = {
  employee: Users,
  leave_request: CalendarDays,
  payroll_run: Wallet,
  deduction_rule: Percent,
  department: Building2,
};

function entityIcon(entity: string): LucideIcon {
  return ENTITY_ICONS[entity] ?? Activity;
}

/** One calendar row: 42 day cells (6 weeks), Monday-first. */
function buildCalendarCells(year: number, month: number) {
  const first = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const lead = (first.getDay() + 6) % 7; // 0 = Monday
  const pad = (n: number) => String(n).padStart(2, "0");
  const cells: { day: number; iso: string; inMonth: boolean }[] = [];
  const prevDays = new Date(year, month - 1, 0).getDate();
  for (let i = lead; i > 0; i--) {
    const m = month - 1;
    const yy = m === 0 ? year - 1 : year;
    const mm = m === 0 ? 12 : m;
    const day = prevDays - i + 1;
    cells.push({ day, iso: `${yy}-${pad(mm)}-${pad(day)}`, inMonth: false });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, iso: `${year}-${pad(month)}-${pad(d)}`, inMonth: true });
  }
  while (cells.length % 7 !== 0) {
    const m = month + 1;
    const yy = m === 13 ? year + 1 : year;
    const mm = m === 13 ? 1 : m;
    const day = cells.length - daysInMonth - lead + 1;
    cells.push({ day, iso: `${yy}-${pad(mm)}-${pad(day)}`, inMonth: false });
  }
  return cells;
}

/* ------------------------------------------------------------------ */
/*  Small components                                                   */
/* ------------------------------------------------------------------ */

function StatCard({ title, value, sub, icon, color }: {
  title: string; value: string | number; sub?: string;
  icon: React.ReactNode; color: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </div>
          <div className={`p-3 rounded-lg ${color}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-dashed border-border py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  );
}

/** Simple percentage bar. */
function Bar({ pct, color = "#2563eb" }: { pct: number; color?: string }) {
  return (
    <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color }}
      />
    </div>
  );
}
/* ------------------------------------------------------------------ */
/*  DashboardPage                                                      */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { user } = useAuth();
  const isStaff = user?.role !== "employee";

  const [ym, setYm] = useState(() => {
    const t = new Date();
    return { y: t.getFullYear(), m: t.getMonth() + 1 };
  });
  const moveMonth = (delta: number) =>
    setYm(({ y, m }) => {
      const d = new Date(y, m - 1 + delta, 1);
      return { y: d.getFullYear(), m: d.getMonth() + 1 };
    });

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
  });

  const { data: schedule } = useQuery({
    queryKey: ["team-schedule", ym.y, ym.m],
    queryFn: () => getTeamSchedule(ym.y, ym.m),
  });

  const cells = useMemo(() => buildCalendarCells(ym.y, ym.m), [ym]);
  const byDay = useMemo(() => {
    const map = new Map<string, TeamDay[]>();
    if (!schedule) return map;
    for (const cell of cells) {
      const hits = schedule.days.filter(
        (b) => b.start_date <= cell.iso && cell.iso <= b.end_date
      );
      if (hits.length) map.set(cell.iso, hits);
    }
    return map;
  }, [cells, schedule]);

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-destructive mt-4">
          Could not load the dashboard. Please try again in a moment.
        </p>
      </div>
    );
  }

  const kpis = summary?.kpis;
  const snap = summary?.payroll_snapshot;
  const trend = (summary?.hiring_trend ?? []).slice(-12);
  const maxHires = Math.max(1, ...trend.map((p) => p.hires));
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  const calTitle = new Date(ym.y, ym.m - 1, 1).toLocaleDateString("en-US", {
    month: "long", year: "numeric",
  });
  const tNow = new Date();
  const todayIso = `${tNow.getFullYear()}-${String(tNow.getMonth() + 1).padStart(2, "0")}-${String(tNow.getDate()).padStart(2, "0")}`;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">{today}</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Active Employees"
          value={kpis?.active_employees ?? "—"}
          sub={kpis ? `${kpis.total_employees} total` : undefined}
          icon={<Users className="h-5 w-5 text-blue-600" />}
          color="bg-blue-50"
        />
        <StatCard
          title="On Leave"
          value={kpis?.on_leave ?? "—"}
          sub="currently away"
          icon={<CalendarDays className="h-5 w-5 text-sky-600" />}
          color="bg-sky-50"
        />
        <StatCard
          title="Pending Leave"
          value={kpis?.pending_leave ?? "—"}
          sub="awaiting approval"
          icon={<Clock className="h-5 w-5 text-amber-600" />}
          color="bg-amber-50"
        />
        <StatCard
          title="Latest Net Payroll"
          value={kpis ? formatMoney(kpis.latest_net_payroll) : "—"}
          sub={snap?.run_id ? `${snap.entry_count} employees paid` : "no run yet"}
          icon={<DollarSign className="h-5 w-5 text-green-600" />}
          color="bg-green-50"
        />
      </div>

      {/* Hiring trend + payroll snapshot (staff views) */}
      {isStaff && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-lg">Hiring trend</CardTitle>
              <Badge variant="secondary" className="text-xs">last 12 months</Badge>
            </CardHeader>
            <CardContent>
              {trend.length === 0 ? (
                <p className="text-sm text-muted-foreground py-6 text-center">
                  {isLoading ? "Loading…" : "No hire data yet."}
                </p>
              ) : (
                <div className="flex items-end gap-2 h-40 pt-2">
                  {trend.map((p) => (
                    <div key={p.month} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        {p.hires || ""}
                      </span>
                      <div
                        className={`w-full max-w-8 rounded-t-md ${p.month === trend[trend.length - 1]?.month ? "bg-blue-600" : "bg-blue-300"}`}
                        style={{
                          height: p.hires ? Math.max(8, (p.hires / maxHires) * 110) : 3,
                        }}
                        title={`${p.month}: ${p.hires} hire${p.hires === 1 ? "" : "s"}`}
                      />
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(`${p.month}-01`).toLocaleDateString("en-US", { month: "short" })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Payroll snapshot</CardTitle>
            </CardHeader>
            <CardContent>
              {!snap?.run_id ? (
                <p className="text-sm text-muted-foreground py-6 text-center">
                  {isLoading ? "Loading…" : "No payroll runs yet."}
                </p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">
                      {formatDate(snap.period_start)} – {formatDate(snap.period_end)}
                    </span>
                    <Badge
                      variant={snap.status === "processed" ? "default" : "secondary"}
                      className="capitalize"
                    >
                      {snap.status}
                    </Badge>
                  </div>
                  <MiniStat label="Total gross" value={formatMoney(snap.total_gross)} />
                  <MiniStat label="Total net paid" value={formatMoney(snap.total_net)} />
                  <MiniStat label="Average net" value={formatMoney(snap.average_net)} />
                  <MiniStat label="Employees" value={String(snap.entry_count)} />
                  <Button asChild variant="outline" size="sm" className="w-full mt-2">
                    <Link to="/payroll">
                      Open payroll <ArrowUpRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Team absence calendar + activity feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-lg">Team absences</CardTitle>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => moveMonth(-1)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm font-semibold w-32 text-center">{calTitle}</span>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => moveMonth(1)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="ml-2"
                onClick={() => {
                  const t = new Date();
                  setYm({ y: t.getFullYear(), m: t.getMonth() + 1 });
                }}
              >
                Today
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-7 text-center text-xs font-semibold text-muted-foreground mb-2">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
                <div key={d}>{d}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
              {cells.map((cell) => {
                const hits = byDay.get(cell.iso) ?? [];
                return (
                  <div
                    key={cell.iso}
                    className={`min-h-[76px] p-1 ${cell.inMonth ? "bg-card" : "bg-muted/40"}`}
                  >
                    <span
                      className={`text-xs ${
                        !cell.inMonth
                          ? "text-muted-foreground/50"
                          : cell.iso === todayIso
                            ? "inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-white font-semibold"
                            : "text-foreground"
                      }`}
                    >
                      {cell.day}
                    </span>
                    <div className="mt-1 space-y-0.5">
                      {hits.slice(0, 3).map((b, j) => (
                        <div
                          key={j}
                          title={`${b.employee_name} · ${b.leave_type} (${b.status})`}
                          className={`truncate rounded px-1 py-px text-[10px] leading-4 ${
                            b.status === "approved"
                              ? "text-white font-medium"
                              : "font-medium"
                          }`}
                          style={
                            b.status === "approved"
                              ? { background: b.color }
                              : {
                                  color: b.color,
                                  border: `1px solid ${b.color}`,
                                  background: "color-mix(in srgb, " + b.color + " 8%, transparent)",
                                }
                          }
                        >
                          {b.employee_name.split(" ")[0]} · {b.leave_type}
                        </div>
                      ))}
                      {hits.length > 3 && (
                        <div className="text-[10px] text-muted-foreground">
                          +{hits.length - 3} more
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> solid = approved
              </span>
              {(summary?.leave_by_type ?? []).map((t) => (
                <span key={t.leave_type} className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: t.color }} />
                  {t.leave_type}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        {isStaff ? (
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-lg">Activity</CardTitle>
              <Button asChild variant="ghost" size="sm">
                <Link to="/audit-logs">
                  All <ArrowUpRight className="h-4 w-4 ml-1" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {(summary?.recent_activity ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground py-6 text-center">
                  {isLoading ? "Loading…" : "No recent activity."}
                </p>
              ) : (
                <ul className="space-y-4">
                  {summary?.recent_activity.map((log) => {
                    const Icon = entityIcon(log.entity);
                    return (
                      <li key={log.id} className="flex gap-3">
                        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                          <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm leading-snug">{describeActivity(log)}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {timeAgo(log.timestamp)}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Hiring</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <TrendingUp className="h-5 w-5 text-blue-500" />
                <p>
                  New this month:{" "}
                  <span className="font-semibold text-foreground">
                    {(() => {
                      const t = new Date();
                      const key = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}`;
                      return summary?.hiring_trend.find((p) => p.month === key)?.hires ?? 0;
                    })()}
                  </span>{" "}
                  in {tNow.toLocaleDateString("en-US", { month: "long" })}
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Analytics row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Headcount by department</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(summary?.headcount_by_department ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                {isLoading ? "Loading…" : "No departments yet."}
              </p>
            ) : (
              (() => {
                const max = Math.max(
                  1,
                  ...summary!.headcount_by_department.map((d) => d.count)
                );
                return summary!.headcount_by_department.map((d) => (
                  <div key={d.department} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{d.department}</span>
                      <span className="text-muted-foreground">
                        {d.active} active / {d.count}
                      </span>
                    </div>
                    <Bar pct={(d.count / max) * 100} />
                  </div>
                ));
              })()
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Leave by type</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(summary?.leave_by_type ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                {isLoading ? "Loading…" : "No leave types yet."}
              </p>
            ) : (
              summary!.leave_by_type.map((t) => (
                <div key={t.leave_type} className="flex items-center justify-between text-sm">
                  <span className="inline-flex items-center gap-2 font-medium">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ background: t.color }}
                    />
                    {t.leave_type}
                  </span>
                  <span className="text-muted-foreground tabular-nums">{t.count} request{t.count === 1 ? "" : "s"}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Balance utilization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(summary?.leave_utilization ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                {isLoading ? "Loading…" : "No balances for this year."}
              </p>
            ) : (
              summary!.leave_utilization.map((u) => (
                <div key={u.leave_type} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="inline-flex items-center gap-2 font-medium">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ background: u.color }}
                      />
                      {u.leave_type}
                    </span>
                    <span className="text-muted-foreground tabular-nums">
                      {u.used}/{u.allocated}d · {u.utilization_pct}%
                    </span>
                  </div>
                  <Bar pct={u.utilization_pct} color={u.color} />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
