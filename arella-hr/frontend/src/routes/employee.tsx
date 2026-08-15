import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getEmployee,
  getPayslips,
  type Payslip,
} from "@/lib/employee";
import { listLeaveBalances, listLeaveRequests, type LeaveRequest } from "@/lib/leave";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PayslipDialog } from "@/features/payroll/Payslip";
import {
  ArrowLeft,
  Building2,
  Cake,
  Check,
  Clock,
  Mail,
  MapPin,
  Phone,
  ReceiptText,
  Users,
  Wallet,
  X,
} from "lucide-react";

function statusVariant(s: string): "default" | "secondary" | "destructive" | "outline" {
  if (s === "active") return "default";
  if (s === "inactive") return "destructive";
  if (s === "on_leave") return "secondary";
  return "outline";
}

function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

function formatMoney(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function tenure(hireDate: string | null): string {
  if (!hireDate) return "—";
  const months = Math.max(
    0,
    (Date.now() - new Date(hireDate).getTime()) / (1000 * 60 * 60 * 24 * 30.44)
  );
  const years = Math.floor(months / 12);
  const rest = Math.round(months % 12);
  if (years === 0) return `${rest} month${rest === 1 ? "" : "s"}`;
  return `${years} year${years === 1 ? "" : "s"}${rest ? ` ${rest} mo` : ""}`;
}

const LEAVE_STATUS_ICON: Record<string, { icon: typeof Check; cls: string }> = {
  approved: { icon: Check, cls: "text-green-600 bg-green-50" },
  pending: { icon: Clock, cls: "text-amber-600 bg-amber-50" },
  rejected: { icon: X, cls: "text-red-600 bg-red-50" },
};

export default function EmployeeProfilePage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const id = Number(employeeId);
  const [openPayslip, setOpenPayslip] = useState<Payslip | null>(null);

  const { data: emp, isLoading, error } = useQuery({
    queryKey: ["employee", id],
    queryFn: () => getEmployee(id).then((r) => r.data),
    enabled: Number.isInteger(id),
  });

  const { data: balances } = useQuery({
    queryKey: ["leave-balances", id, "profile"],
    queryFn: () => listLeaveBalances(id, new Date().getFullYear()),
    enabled: !!emp,
  });

  const { data: allRequests } = useQuery({
    queryKey: ["leave-requests", "all"],
    queryFn: () => listLeaveRequests(1, 100),
    enabled: !!emp,
  });

  const { data: payslips } = useQuery({
    queryKey: ["payslips", id],
    queryFn: () => getPayslips(id),
    enabled: !!emp,
  });

  const leaveHistory = useMemo(
    () => (allRequests?.items ?? []).filter((r: LeaveRequest) => r.employee_id === id),
    [allRequests, id]
  );

  if (error) {
    return (
      <div className="p-8">
        <BackLink />
        <p className="text-sm text-destructive mt-4">Could not load this employee.</p>
      </div>
    );
  }

  if (isLoading || !emp) {
    return (
      <div className="p-8">
        <BackLink />
        <p className="text-sm text-muted-foreground mt-4">Loading profile…</p>
      </div>
    );
  }

  const initials = `${emp.first_name.charAt(0)}${emp.last_name.charAt(0)}`;
  const latestPay = payslips?.[0];

  return (
    <div className="p-8 space-y-6">
      <BackLink />

      {/* Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-5">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-2xl font-bold text-white">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight">
                  {emp.first_name} {emp.last_name}
                </h1>
                <Badge variant={statusVariant(emp.status)}>{emp.status.replace("_", " ")}</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {[emp.position, emp.department].filter(Boolean).join(" · ")}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" /> {emp.email}
                </span>
                {emp.phone && (
                  <span className="inline-flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5" /> {emp.phone}
                  </span>
                )}
                {emp.manager_name && (
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5" /> Reports to {emp.manager_name}
                  </span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details + balances + pay */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow icon={Cake} label="Hire date" value={`${formatDate(emp.hire_date)} · ${tenure(emp.hire_date)}`} />
            <DetailRow icon={Wallet} label="Base salary" value={formatMoney(emp.salary_base)} />
            <DetailRow icon={Building2} label="Department" value={emp.department ?? "—"} />
            <DetailRow icon={MapPin} label="Address" value={emp.address ?? "—"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Leave balances · {new Date().getFullYear()}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(balances ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No balances yet.</p>
            ) : (
              balances!.map((b) => (
                <div key={b.id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{b.leave_type_name}</span>
                    <span className="text-muted-foreground tabular-nums">
                      {b.used}/{b.allocated}d
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(100, b.utilization_pct)}%`,
                        background: "currentColor",
                        color: b.utilization_pct > 100 ? "#dc2626" : "#2563eb",
                      }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {b.remaining > 0 ? `${b.remaining}d remaining` : "Fully used"}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Latest pay</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!latestPay ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No payroll entries yet.</p>
            ) : (
              <>
                <p className="text-3xl font-bold tabular-nums">
                  {latestPay.net_pay.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                </p>
                <p className="text-xs text-muted-foreground">
                  Net pay · {formatDate(latestPay.period_start)} – {formatDate(latestPay.period_end)}
                </p>
                <div className="flex items-center justify-between border-t border-dashed border-border pt-3 text-sm">
                  <span className="text-muted-foreground">Gross</span>
                  <span className="font-medium tabular-nums">
                    {latestPay.gross_salary.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => setOpenPayslip(latestPay)}
                >
                  <ReceiptText className="h-4 w-4 mr-2" />
                  View payslip
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Leave history + payslips */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Leave history</CardTitle>
          </CardHeader>
          <CardContent>
            {leaveHistory.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">No leave requests yet.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Period</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Days</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaveHistory.map((r) => {
                    const meta = LEAVE_STATUS_ICON[r.status] ?? LEAVE_STATUS_ICON.pending;
                    const Icon = meta.icon;
                    return (
                      <TableRow key={r.id}>
                        <TableCell>
                          <p className="text-sm font-medium">
                            {formatDate(r.start_date)} – {formatDate(r.end_date)}
                          </p>
                          {r.manager_note && (
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                              “{r.manager_note}”
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1.5 text-sm">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ background: r.leave_type_color }} />
                            {r.leave_type_name}
                          </span>
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">{r.days_requested}</TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${meta.cls}`}>
                            <Icon className="h-3 w-3" />
                            {r.status}
                          </span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Payslips</CardTitle>
          </CardHeader>
          <CardContent>
            {(payslips ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">No payslips yet.</p>
            ) : (
              <ul className="divide-y divide-border">
                {payslips!.map((p) => (
                  <li key={p.entry_id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium">
                        {formatDate(p.period_start)} – {formatDate(p.period_end)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Gross {formatMoney(p.gross_salary)} · Deductions −
                        {formatMoney(p.deductions)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold tabular-nums">
                        {p.net_pay.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                      </span>
                      <Button variant="ghost" size="sm" onClick={() => setOpenPayslip(p)}>
                        <ReceiptText className="h-4 w-4 mr-1.5" />
                        View
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <PayslipDialog payslip={openPayslip} open={!!openPayslip} onOpenChange={(o) => !o && setOpenPayslip(null)} />
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/employees" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
      <ArrowLeft className="h-4 w-4" />
      Back to employees
    </Link>
  );
}

function DetailRow({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium break-words">{value}</p>
      </div>
    </div>
  );
}
