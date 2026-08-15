import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { differenceInCalendarDays } from "date-fns";
import { Check, X, Clock, CalendarDays, Plus, Ban, User } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { listLeaveRequests, createLeaveRequest, approveLeaveRequest, rejectLeaveRequest, cancelLeaveRequest, listLeaveTypes, listDepartments, listLeaveBalances, type LeaveRequest, type LeaveRequestCreate, type LeaveType, type Department } from "@/lib/leave";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { toast } from "@/hooks/use-toast";

function statusBadgeVariant(s: string): "default"|"secondary"|"destructive"|"outline" {
  if (s === "approved") return "default";
  if (s === "rejected") return "destructive";
  return "secondary";
}

function formatDate(d: string): string {
  try { return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  catch { return "—"; }
}

function daysBetween(start: string, end: string): number {
  if (!start || !end) return 0;
  return differenceInCalendarDays(new Date(end), new Date(start));
}

/* ------------------------------------------------------------------ */
/*  StatusBadge component                                               */
/* ------------------------------------------------------------------ */

function StatusBadge({ status }: { status: LeaveRequest["status"] }) {
  return (
    <Badge variant={statusBadgeVariant(status)}>
      {status === "approved" && <Check className="mr-1 h-3 w-3" />}
      {status === "rejected" && <X className="mr-1 h-3 w-3" />}
      {status === "pending" && <Clock className="mr-1 h-3 w-3" />}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  StatCard component                                                  */
/* ------------------------------------------------------------------ */

function StatCard({ title, value, icon, bgColor }: {
  title: string; value: string | number; icon: React.ReactNode; bgColor: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
          <div className={`p-3 rounded-lg ${bgColor}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  LeaveFormDialog component                                           */
/* ------------------------------------------------------------------ */

function LeaveFormDialog({ leaveTypes, departments, onClose, onSubmit }: {
  leaveTypes: LeaveType[];
  departments: Department[];
  onClose: () => void;
  onSubmit: (data: LeaveRequestCreate) => void;
}) {
  const [form, setForm] = useState<LeaveRequestCreate>({
    leave_type_id: leaveTypes[0]?.id ?? 0,
    start_date: new Date().toISOString().split("T")[0],
    end_date: new Date().toISOString().split("T")[0],
    reason: "",
  });

  const calcDays = () => daysBetween(form.start_date, form.end_date);

  const handleOk = (e: React.FormEvent) => {
    e.preventDefault();
    if (calcDays() <= 0) { toast.error("End date must be after start date"); return; }
    onSubmit({ ...form, reason: form.reason || undefined });
  };

  const upd = (k: keyof LeaveRequestCreate, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Request Leave</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleOk} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="leave-type">Leave Type</Label>
              <Select value={form.leave_type_id.toString()} onValueChange={(v) => setForm((f) => ({ ...f, leave_type_id: Number(v) }))}>
                <SelectTrigger id="leave-type"><SelectValue placeholder="Select type" /></SelectTrigger>
                <SelectContent>
                  {leaveTypes.map((t) => (
                    <SelectItem key={t.id} value={t.id.toString()}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="department">Department (optional)</Label>
              <Select value="" onValueChange={() => {}}>
                <SelectTrigger id="department"><SelectValue placeholder="Select department" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No Department</SelectItem>
                  {departments.map((d) => (
                    <SelectItem key={d.id} value={d.id.toString()}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start">Start Date</Label>
              <Input id="start" type="date" value={form.start_date} onChange={(e) => upd("start_date", e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end">End Date</Label>
              <Input id="end" type="date" value={form.end_date} onChange={(e) => upd("end_date", e.target.value)} required />
            </div>
          </div>
          {calcDays() > 0 && (
            <div className="p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
              Duration: {calcDays()} working day{calcDays() > 1 ? "s" : ""}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Textarea id="reason" value={form.reason} onChange={(e) => upd("reason", e.target.value)} placeholder="Brief reason for leave request..." rows={3} />
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancel</Button></DialogClose>
            <Button type="submit">Submit Request</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  LeavePage component                                                  */
/* ------------------------------------------------------------------ */

export default function LeavePage() {
  const { user } = useAuth();
  const role = user?.role;
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"my_requests" | "approval_queue">("my_requests");
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const isAdminOrManager = role === "admin" || role === "manager";

  const { data: paginated, isLoading } = useQuery({
    queryKey: ["leave-requests", { page, status: statusFilter }],
    queryFn: () => listLeaveRequests(page, pageSize, statusFilter),
  });

  const { data: leaveTypes } = useQuery({
    queryKey: ["leave-types"],
    queryFn: () => listLeaveTypes(),
  });

  const { data: departments } = useQuery({
    queryKey: ["departments"],
    queryFn: () => listDepartments(),
  });

  const { data: balances } = useQuery({
    queryKey: ["leave-balances", { employeeId: user?.id }],
    queryFn: () => listLeaveBalances(user?.id),
  });

  const createMutation = useMutation({
    mutationFn: (data: LeaveRequestCreate) => createLeaveRequest(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      qc.invalidateQueries({ queryKey: ["leave-balances"] });
      setShowForm(false);
      toast.success("Leave request submitted successfully");
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) => approveLeaveRequest(id, { manager_note: note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      qc.invalidateQueries({ queryKey: ["leave-balances"] });
      toast.success("Leave request approved");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => rejectLeaveRequest(id, { manager_note: note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      toast.success("Leave request rejected");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => cancelLeaveRequest(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      qc.invalidateQueries({ queryKey: ["leave-balances"] });
      toast.success("Leave request cancelled");
    },
  });

  const items = paginated?.items ?? [];
  const totalPages = paginated?.total_pages ?? 0;
  const pendingItems = items.filter((i) => i.status === "pending");
  const myRequests = items.filter((i) => i.employee_id === user?.id);
  const showMyRequests = !isAdminOrManager || activeTab === "my_requests";

  const totalAll = items.length;
  const totalPending = items.filter((i) => i.status === "pending").length;
  const totalApproved = items.filter((i) => i.status === "approved").length;
  const totalRejected = items.filter((i) => i.status === "rejected").length;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leave Management</h1>
          <p className="text-muted-foreground mt-1">Manage leave requests, approvals, and balances.</p>
        </div>
        {showMyRequests && (
          <Button onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Request Leave
          </Button>
        )}
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Total Requests" value={totalAll} icon={<CalendarDays className="h-5 w-5 text-blue-600" />} bgColor="bg-blue-50" />
        <StatCard title="Pending" value={totalPending} icon={<Clock className="h-5 w-5 text-amber-600" />} bgColor="bg-amber-50" />
        <StatCard title="Approved" value={totalApproved} icon={<Check className="h-5 w-5 text-green-600" />} bgColor="bg-green-50" />
        <StatCard title="Rejected" value={totalRejected} icon={<X className="h-5 w-5 text-red-600" />} bgColor="bg-red-50" />
      </div>

      {/* Leave Balances (if available) */}
      {balances && balances.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Leave Balances</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {balances.map((b) => (
                <div key={b.id} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{b.leave_type_name}</span>
                    <span className="text-sm text-muted-foreground">{b.year}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">{b.remaining} remaining</span>
                    <span className="text-muted-foreground">of {b.allocated}</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(b.utilization_pct, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">{b.utilization_pct.toFixed(0)}% utilized</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs & Filter */}
      {isAdminOrManager && (
        <div className="flex items-center gap-4">
          <div className="flex gap-1">
            <Button
              variant={activeTab === "my_requests" ? "default" : "ghost"}
              onClick={() => { setActiveTab("my_requests"); setPage(1); }}
            >
              <User className="h-4 w-4 mr-2" />
              My Requests ({myRequests.length})
            </Button>
            <Button
              variant={activeTab === "approval_queue" ? "default" : "ghost"}
              onClick={() => { setActiveTab("approval_queue"); setPage(1); }}
            >
              <Clock className="h-4 w-4 mr-2" />
              Approval Queue ({pendingItems.length})
            </Button>
          </div>
          <Select value={statusFilter ?? ""} onValueChange={(v) => { setStatusFilter(v || undefined); setPage(1); }}>
            <SelectTrigger className="w-[160px]"><SelectValue placeholder="All statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Data Table */}
      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex justify-center py-8 text-muted-foreground">Loading...</div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
              <CalendarDays className="h-10 w-10 opacity-40" />
              <p>No leave requests found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Dates</TableHead>
                  <TableHead>Days</TableHead>
                  {isAdminOrManager && <TableHead>Department</TableHead>}
                  <TableHead>Status</TableHead>
                  <TableHead>Reason</TableHead>
                  {isAdminOrManager && <TableHead>Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {req.employee_avatar_url ? (
                          <img src={req.employee_avatar_url} alt="" className="h-8 w-8 rounded-full" />
                        ) : (
                          <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                            {req.employee_name.charAt(0).toUpperCase()}
                          </div>
                        )}
                        <span className="font-medium">{req.employee_name}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1.5">
                        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: req.leave_type_color }} />
                        {req.leave_type_name}
                        {req.leave_type_is_paid && <span className="text-xs text-muted-foreground">(Paid)</span>}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>{formatDate(req.start_date)}</div>
                        <div className="text-muted-foreground">to {formatDate(req.end_date)}</div>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{req.days_requested}</TableCell>
                    {isAdminOrManager && (
                      <TableCell className="text-muted-foreground">
                        {req.department_name ?? "—"}
                      </TableCell>
                    )}
                    <TableCell><StatusBadge status={req.status} /></TableCell>
                    <TableCell className="max-w-[200px] truncate text-muted-foreground">{req.reason ?? "—"}</TableCell>
                    {isAdminOrManager && (
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {req.status === "pending" && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => approveMutation.mutate({ id: req.id })}
                                disabled={approveMutation.isPending}
                              >
                                <Check className="h-4 w-4 text-green-600" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => rejectMutation.mutate({ id: req.id, note: "" })}
                                disabled={rejectMutation.isPending}
                              >
                                <X className="h-4 w-4 text-red-600" />
                              </Button>
                            </>
                          )}
                          {(req.status === "pending" || req.status === "approved") && req.employee_id === user?.id && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => cancelMutation.mutate(req.id)}
                              disabled={cancelMutation.isPending}
                            >
                              <Ban className="h-4 w-4 text-amber-600" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious onClick={() => setPage((p) => Math.max(1, p - 1))} />
            </PaginationItem>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <PaginationItem key={p}>
                <PaginationLink
                  isActive={p === page}
                  onClick={() => setPage(p)}
                >
                  {p}
                </PaginationLink>
              </PaginationItem>
            ))}
            <PaginationItem>
              <PaginationNext onClick={() => setPage((p) => Math.min(totalPages, p + 1))} />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      {/* Leave Form Dialog */}
      {showForm && (
        <LeaveFormDialog
          leaveTypes={leaveTypes ?? []}
          departments={departments ?? []}
          onClose={() => setShowForm(false)}
          onSubmit={(data) => createMutation.mutate(data)}
        />
      )}
    </div>
  );
}