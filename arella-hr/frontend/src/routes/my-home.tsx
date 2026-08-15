import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMyProfile,
  getPayslips,
  type Payslip,
} from "@/lib/employee";
import {
  listLeaveBalances,
  listLeaveRequests,
  listLeaveTypes,
  createLeaveRequest,
  cancelLeaveRequest,
  type LeaveRequest,
  type LeaveRequestCreate,
} from "@/lib/leave";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PayslipDialog } from "@/features/payroll/Payslip";
import {
  CalendarPlus,
  Check,
  Clock,
  ReceiptText,
  X,
} from "lucide-react";
import { toast } from "@/hooks/use-toast";

function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

const STATUS_ICON: Record<string, { icon: typeof Check; cls: string }> = {
  approved: { icon: Check, cls: "text-green-600 bg-green-50" },
  pending: { icon: Clock, cls: "text-amber-600 bg-amber-50" },
  rejected: { icon: X, cls: "text-red-600 bg-red-50" },
};

export default function MyHomePage() {
  const qc = useQueryClient();
  const [requestOpen, setRequestOpen] = useState(false);
  const [cancelReq, setCancelReq] = useState<LeaveRequest | null>(null);
  const [openPayslip, setOpenPayslip] = useState<Payslip | null>(null);

  const { data: me, isLoading, error } = useQuery({
    queryKey: ["my-profile"],
    queryFn: getMyProfile,
  });

  const year = new Date().getFullYear();

  const { data: balances } = useQuery({
    queryKey: ["leave-balances", me?.id, year, "myhome"],
    queryFn: () => listLeaveBalances(me!.id, year),
    enabled: !!me,
  });

  const { data: requests } = useQuery({
    queryKey: ["leave-requests", "mine"],
    queryFn: () => listLeaveRequests(1, 50),
    enabled: !!me,
  });

  const { data: payslips } = useQuery({
    queryKey: ["payslips", me?.id],
    queryFn: () => getPayslips(me!.id),
    enabled: !!me,
  });

  const mCancel = useMutation({
    mutationFn: cancelLeaveRequest,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      qc.invalidateQueries({ queryKey: ["leave-balances"] });
      setCancelReq(null);
      toast.success("Leave request cancelled");
    },
  });

  if (error) {
    return (
      <div className="p-8 space-y-4">
        <h1 className="text-2xl font-bold tracking-tight">My Home</h1>
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Your account isn’t linked to an employee record yet.</p>
            <p className="mt-1">Contact HR to connect your login with your profile.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading || !me) {
    return (
      <div className="p-8">
        <p className="text-sm text-muted-foreground">Loading your home…</p>
      </div>
    );
  }

  const myRequests = requests?.items ?? [];
  const latestPay = payslips?.[0];

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-xl font-bold text-white">
            {me.first_name.charAt(0)}
            {me.last_name.charAt(0)}
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Hi {me.first_name} 👋
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {[me.position, me.department].filter(Boolean).join(" · ") || "Employee"}
            </p>
          </div>
        </div>
        <Button onClick={() => setRequestOpen(true)}>
          <CalendarPlus className="h-4 w-4 mr-2" />
          Request leave
        </Button>
      </div>

      {/* Balances + pay */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Leave balances · {year}</CardTitle>
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
              <p className="text-sm text-muted-foreground py-4 text-center">No payslips yet.</p>
            ) : (
              <>
                <p className="text-3xl font-bold tabular-nums">
                  {latestPay.net_pay.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                </p>
                <p className="text-xs text-muted-foreground">
                  Net pay · {formatDate(latestPay.period_start)} – {formatDate(latestPay.period_end)}
                </p>
                <ul className="divide-y divide-border border-t border-border pt-1">
                  {payslips!.slice(0, 3).map((p) => (
                    <li key={p.entry_id} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-muted-foreground">
                        {formatDate(p.period_start)} – {formatDate(p.period_end)}
                      </span>
                      <button
                        className="inline-flex items-center gap-1 text-blue-600 hover:underline text-xs font-medium"
                        onClick={() => setOpenPayslip(p)}
                      >
                        <ReceiptText className="h-3.5 w-3.5" /> Payslip
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Leave history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">My leave requests</CardTitle>
        </CardHeader>
        <CardContent>
          {myRequests.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No leave requests yet. Use “Request leave” to get started.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Days</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {myRequests.map((r) => {
                  const meta = STATUS_ICON[r.status] ?? STATUS_ICON.pending;
                  const Icon = meta.icon;
                  return (
                    <TableRow key={r.id}>
                      <TableCell>
                        <p className="text-sm font-medium">
                          {formatDate(r.start_date)} – {formatDate(r.end_date)}
                        </p>
                        {r.reason && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{r.reason}</p>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5 text-sm">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ background: r.leave_type_color }}
                          />
                          {r.leave_type_name}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">{r.days_requested}</TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${meta.cls}`}
                        >
                          <Icon className="h-3 w-3" />
                          {r.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        {r.status === "pending" && (
                          <Button variant="ghost" size="sm" onClick={() => setCancelReq(r)}>
                            Cancel
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <LeaveRequestDialog open={requestOpen} onOpenChange={setRequestOpen} onCreated={() => {
        qc.invalidateQueries({ queryKey: ["leave-requests"] });
        qc.invalidateQueries({ queryKey: ["leave-balances"] });
      }} />

      <AlertDialog open={!!cancelReq} onOpenChange={(o) => !o && setCancelReq(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel this request?</AlertDialogTitle>
            <AlertDialogDescription>
              {cancelReq && (
                <>
                  {cancelReq.leave_type_name}, {formatDate(cancelReq.start_date)} –{" "}
                  {formatDate(cancelReq.end_date)}. This cannot be undone.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep request</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={() => cancelReq && mCancel.mutate(cancelReq.id)}
            >
              Cancel request
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <PayslipDialog
        payslip={openPayslip}
        open={!!openPayslip}
        onOpenChange={(o) => !o && setOpenPayslip(null)}
      />
    </div>
  );
}

function LeaveRequestDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreated: () => void;
}) {
  const { data: types } = useQuery({
    queryKey: ["leave-types"],
    queryFn: () => listLeaveTypes(true),
  });

  const [typeId, setTypeId] = useState<string>("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mCreate = useMutation({
    mutationFn: (d: LeaveRequestCreate) => createLeaveRequest(d),
    onSuccess: () => {
      onCreated();
      onOpenChange(false);
      setStart("");
      setEnd("");
      setReason("");
      setError(null);
      toast.success("Leave request submitted for approval");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not submit this request.");
    },
  });

  function submit() {
    if (!typeId || !start || !end) return;
    if (new Date(end) < new Date(start)) {
      setError("End date must be on or after the start date.");
      return;
    }
    mCreate.mutate({
      leave_type_id: Number(typeId),
      start_date: start,
      end_date: end,
      reason: reason.trim() || undefined,
    });
  }

  const valid = !!typeId && !!start && !!end && new Date(end) >= new Date(start);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request leave</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Leave type</Label>
            <Select value={typeId} onValueChange={setTypeId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a leave type" />
              </SelectTrigger>
              <SelectContent>
                {(types ?? []).map((t) => (
                  <SelectItem key={t.id} value={String(t.id)}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mr-start">Start date</Label>
              <Input
                id="mr-start"
                type="date"
                value={start}
                min={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mr-end">End date</Label>
              <Input
                id="mr-end"
                type="date"
                value={end}
                min={start || new Date().toISOString().slice(0, 10)}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="mr-reason">Reason (optional)</Label>
            <Input
              id="mr-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Family trip"
            />
          </div>
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={!valid || mCreate.isPending}>
              {mCreate.isPending ? "Submitting…" : "Submit request"}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
