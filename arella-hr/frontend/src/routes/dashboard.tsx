import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Users, Clock, DollarSign, CalendarDays, ArrowUpRight } from "lucide-react";
import { listEmployees, type Employee } from "@/lib/employee";
import { listLeaveRequests, type LeaveRequest } from "@/lib/leave";
import { listPayrollRuns, type PayrollRunOut } from "@/lib/payroll";
import { listDepartments, type Department } from "@/lib/leave";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusVariant(s: string): "default" | "secondary" | "destructive" {
  if (s === "approved") return "default";
  if (s === "rejected") return "destructive";
  return "secondary";
}

function statusLabel(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatMoney(v: number): string {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

/* ------------------------------------------------------------------ */
/*  StatCard                                                           */
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

/* ------------------------------------------------------------------ */
/*  DashboardPage                                                      */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { data: employeesData } = useQuery({
    queryKey: ["employees", { page: 1, page_size: 100, status: "active" }],
    queryFn: () =>
      listEmployees({ page: 1, page_size: 100, status: "active" }).then((r) => r.data),
  });

  const { data: leaveData } = useQuery({
    queryKey: ["leave-requests", { page: 1, page_size: 50 }],
    queryFn: () => listLeaveRequests(1, 50),
  });

  const { data: runs } = useQuery({
    queryKey: ["payroll-runs"],
    queryFn: () => listPayrollRuns(),
  });

  const { data: departments } = useQuery({
    queryKey: ["departments"],
    queryFn: () => listDepartments(),
  });

  const activeEmployees: Employee[] = employeesData?.items ?? [];
  const totalEmployees = employeesData?.total ?? 0;
  const allLeave: LeaveRequest[] = leaveData?.items ?? [];
  const pendingLeave = allLeave.filter((r) => r.status === "pending");
  const recentLeave = allLeave.slice(0, 6);
  // Latest run by period (not necessarily a draft) — keeps the card useful
  // even after the current draft has been processed.
  const runItems = runs?.items ?? [];
  const latestRun: PayrollRunOut | undefined = runItems.length
    ? [...runItems].sort((a, b) => (a.period_start < b.period_start ? 1 : -1))[0]
    : undefined;
  const payrollTotal = latestRun?.total_net ?? 0;
  const runMonth = latestRun
    ? new Date(latestRun.period_start).toLocaleDateString("en-US", { month: "long" })
    : null;

  // Departments with headcount (any status — the demo shows the org chart).
  const deptHeadcount = (departments ?? []).map((d: Department) => {
    const count = activeEmployees.filter((e) => e.department === d.name).length;
    return { name: d.name, count };
  });
  const maxDept = Math.max(1, ...deptHeadcount.map((d) => d.count));

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  const loading = !employeesData && !leaveData;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">{today}</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Active Employees"
          value={totalEmployees}
          icon={<Users className="h-5 w-5 text-blue-600" />}
          color="bg-blue-50"
        />
        <StatCard
          title="Pending Leave Requests"
          value={pendingLeave.length}
          icon={<Clock className="h-5 w-5 text-amber-600" />}
          color="bg-amber-50"
        />
        <StatCard
          title={latestRun ? `${runMonth} Payroll` : "Payroll"}
          value={formatMoney(payrollTotal)}
          sub={latestRun ? `${latestRun.status} · ${latestRun.entry_count} staff` : undefined}
          icon={<DollarSign className="h-5 w-5 text-green-600" />}
          color="bg-green-50"
        />
        <StatCard
          title="Leave Requests (all)"
          value={allLeave.length}
          icon={<CalendarDays className="h-5 w-5 text-violet-600" />}
          color="bg-violet-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Leave Requests */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-lg">Recent Leave Requests</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to="/leave">
                View all <ArrowUpRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recentLeave.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                {loading ? "Loading…" : "No leave requests yet."}
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Employee</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Days</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentLeave.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.employee_name}</TableCell>
                      <TableCell>{r.leave_type_name}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {new Date(r.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        {" – "}
                        {new Date(r.end_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </TableCell>
                      <TableCell>{r.days_requested}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(r.status)}>{statusLabel(r.status)}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Departments */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Departments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {deptHeadcount.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                {loading ? "Loading…" : "No departments yet."}
              </p>
            ) : (
              deptHeadcount.map((d) => (
                <div key={d.name} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{d.name}</span>
                    <span className="text-muted-foreground">{d.count} active</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${(d.count / maxDept) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
