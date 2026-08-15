import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import {
  listPayrollRuns, createPayrollRun, processPayrollRun, deletePayrollRun,
  listPayrollEntries,
  type PayrollRunOut, type PayrollRunCreate,
} from "@/lib/payroll";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Eye, Plus, Trash2, Play, ChevronLeft, ChevronRight,
  DollarSign, Users, Calendar, TrendingUp, Search,
} from "lucide-react";
import { toast } from "@/hooks/use-toast";

function statusBadgeClass(status: string): string {
  if (status === "draft") return "bg-yellow-100 text-yellow-800 border-yellow-200";
  if (status === "processed") return "bg-blue-100 text-blue-800 border-blue-200";
  if (status === "paid") return "bg-green-100 text-green-800 border-green-200";
  return "bg-gray-100 text-gray-800";
}

function formatDate(d: string | null): string {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  catch { return "—"; }
}

function formatCurrency(v: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
}

// ── Create Payroll Run Dialog ──────────────────────────────────────────────────

function CreateRunDialog({ open, onOpenChange, onSubmit }: {
  open: boolean; onOpenChange: (o: boolean) => void;
  onSubmit: (d: PayrollRunCreate) => void;
}) {
  const [form, setForm] = useState<{ period_start: string; period_end: string; notes: string }>({
    period_start: "", period_end: "", notes: "",
  });
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.period_start || !form.period_end) return;
    onSubmit({ period_start: form.period_start, period_end: form.period_end, notes: form.notes || undefined });
    setForm({ period_start: "", period_end: "", notes: "" });
  };
  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Create Payroll Run</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ps">Period Start</Label>
              <Input id="ps" type="date" value={form.period_start} onChange={(e) => upd("period_start", e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pe">Period End</Label>
              <Input id="pe" type="date" value={form.period_end} onChange={(e) => upd("period_end", e.target.value)} required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Input id="notes" value={form.notes} onChange={(e) => upd("notes", e.target.value)} placeholder="e.g. Monthly payroll for June" />
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancel</Button></DialogClose>
            <Button type="submit" disabled={!form.period_start || !form.period_end}>Create Run</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── View Entries Modal ─────────────────────────────────────────────────────────

function ViewEntriesModal({ run, open, onOpenChange }: {
  run: PayrollRunOut; open: boolean; onOpenChange: (o: boolean) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["payroll-entries", run.id],
    queryFn: () => listPayrollEntries(run.id),
    enabled: open,
  });
  const entries = data?.items ?? [];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Payroll Entries — {formatDate(run.period_start)} to {formatDate(run.period_end)}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <p className="py-8 text-center text-muted-foreground">Loading entries…</p>
        ) : (
          <div className="overflow-auto max-h-[60vh]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Deductions</TableHead>
                  <TableHead className="text-right">Bonuses</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">No entries yet — process this run first.</TableCell></TableRow>
                ) : (
                  entries.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell className="font-medium">{e.employee_name}</TableCell>
                      <TableCell className="text-right">{formatCurrency(e.gross_salary)}</TableCell>
                      <TableCell className="text-right text-red-600">-{formatCurrency(e.deductions)}</TableCell>
                      <TableCell className="text-right text-green-600">+{formatCurrency(e.bonuses)}</TableCell>
                      <TableCell className="text-right font-semibold">{formatCurrency(e.net_pay)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            {entries.length > 0 && (
              <div className="flex justify-end gap-6 mt-4 pt-4 border-t text-sm">
                <span>Entries: <strong>{entries.length}</strong></span>
                <span>Total Gross: <strong>{formatCurrency(entries.reduce((s, e) => s + e.gross_salary, 0))}</strong></span>
                <span>Total Net: <strong>{formatCurrency(entries.reduce((s, e) => s + e.net_pay, 0))}</strong></span>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Main Payroll Runs Component ────────────────────────────────────────────────

export function PayrollRuns() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [debounced, setDebounced] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewingRun, setViewingRun] = useState<PayrollRunOut | null>(null);
  const [confirmProcess, setConfirmProcess] = useState<PayrollRunOut | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<PayrollRunOut | null>(null);

  useEffect(() => { const t = setTimeout(() => setDebounced(search), 300); return () => clearTimeout(t); }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: ["payroll-runs", { page, pageSize, search: debounced, status: statusFilter }],
    queryFn: () => listPayrollRuns({ page, page_size: pageSize, search: debounced || undefined, status: statusFilter || undefined }),
  });

  const mCreate = useMutation({
    mutationFn: createPayrollRun,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["payroll-runs"] }); setCreateOpen(false); toast.success("Payroll run created"); },
  });
  const mProcess = useMutation({
    mutationFn: processPayrollRun,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["payroll-runs"] }); setConfirmProcess(null); toast.success("Payroll run processed"); },
  });
  const mDelete = useMutation({
    mutationFn: deletePayrollRun,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["payroll-runs"] }); setConfirmDelete(null); toast.success("Payroll run deleted"); },
  });

  const totalRuns = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 0;
  const runs = data?.items ?? [];
  const totalGross = runs.reduce((s, r) => s + r.total_gross, 0);
  const draftCount = runs.filter((r) => r.status === "draft").length;
  const processedCount = runs.filter((r) => r.status === "processed").length;

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Total Runs</p><p className="text-2xl font-bold">{totalRuns}</p></div>
              <div className="p-3 rounded-lg bg-blue-50"><Calendar className="h-5 w-5 text-blue-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Draft</p><p className="text-2xl font-bold">{draftCount}</p></div>
              <div className="p-3 rounded-lg bg-yellow-50"><Users className="h-5 w-5 text-yellow-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Processed</p><p className="text-2xl font-bold">{processedCount}</p></div>
              <div className="p-3 rounded-lg bg-blue-50"><TrendingUp className="h-5 w-5 text-blue-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Total Gross</p><p className="text-2xl font-bold">{formatCurrency(totalGross)}</p></div>
              <div className="p-3 rounded-lg bg-green-50"><DollarSign className="h-5 w-5 text-green-600" /></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Toolbar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search payroll runs…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="pl-10" />
            </div>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
              <SelectTrigger className="w-full sm:w-[160px]"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="processed">Processed</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
              </SelectContent>
            </Select>
            {isAdmin && (
              <Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4 mr-2" />New Run</Button>
            )}
          </div>

          {/* Table */}
          <div className="mt-4">
            {isLoading ? (
              <p className="py-8 text-center text-muted-foreground">Loading payroll runs…</p>
            ) : runs.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">No payroll runs found. Create one to get started.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Period</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Gross</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                    <TableHead className="text-center">Entries</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[120px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>
                        <div className="font-medium">{formatDate(run.period_start)}</div>
                        <div className="text-xs text-muted-foreground">{formatDate(run.period_end)}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={statusBadgeClass(run.status)}>
                          {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(run.total_gross)}</TableCell>
                      <TableCell className="text-right font-semibold">{formatCurrency(run.total_net)}</TableCell>
                      <TableCell className="text-center">{run.entry_count}</TableCell>
                      <TableCell>{formatDate(run.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setViewingRun(run)} title="View Entries">
                            <Eye className="h-4 w-4" />
                          </Button>
                          {(run.status === "draft" || run.status === "processed") && isAdmin && (
                            <Button size="sm" variant="ghost" onClick={() => setConfirmProcess(run)} title="Process Run">
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {run.status === "draft" && isAdmin && (
                            <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(run)} title="Delete Run">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages} ({totalRuns} total)
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    <ChevronLeft className="h-4 w-4 mr-1" />Previous
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                    Next<ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <CreateRunDialog open={createOpen} onOpenChange={setCreateOpen} onSubmit={(d) => mCreate.mutate(d)} />

      {viewingRun && (
        <ViewEntriesModal run={viewingRun} open={!!viewingRun} onOpenChange={(o) => { if (!o) setViewingRun(null); }} />
      )}

      {confirmProcess && (
        <AlertDialog open={!!confirmProcess} onOpenChange={(o) => { if (!o) setConfirmProcess(null); }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Process Payroll Run</AlertDialogTitle>
              <AlertDialogDescription>
                This will calculate pay for all employees in the period {formatDate(confirmProcess.period_start)} to {formatDate(confirmProcess.period_end)}.
                Entries cannot be undone. Are you sure?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => mProcess.mutate(confirmProcess.id)} className="bg-blue-600 hover:bg-blue-700">
                Process Run
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {confirmDelete && (
        <AlertDialog open={!!confirmDelete} onOpenChange={(o) => { if (!o) setConfirmDelete(null); }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Payroll Run</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete the payroll run for {formatDate(confirmDelete.period_start)} to {formatDate(confirmDelete.period_end)}? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => mDelete.mutate(confirmDelete.id)} className="bg-red-600 hover:bg-red-700">
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}