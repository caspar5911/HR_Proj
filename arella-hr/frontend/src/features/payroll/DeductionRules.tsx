import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import {
  listDeductionRules, createDeductionRule, updateDeductionRule, deleteDeductionRule,
  type DeductionRuleOut, type DeductionRuleCreate, type DeductionRuleUpdate,
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
  Plus, Trash2, Edit, Search, ChevronLeft, ChevronRight, Settings2,
} from "lucide-react";
import { toast } from "@/hooks/use-toast";

function formatValue(rule: DeductionRuleOut): string {
  if (rule.deduction_type === "percentage") return `${rule.value}%`;
  return `$${rule.value.toLocaleString("en-US")}`;
}

function formatDate(d: string): string {
  try { return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  catch { return "—"; }
}

// ── Rule Form Dialog ──────────────────────────────────────────────────────────

function RuleFormDialog({ open, onOpenChange, rule, onSubmit }: {
  open: boolean; onOpenChange: (o: boolean) => void;
  rule: DeductionRuleOut | null; onSubmit: (d: DeductionRuleCreate | DeductionRuleUpdate) => void;
}) {
  const [form, setForm] = useState<{ name: string; description: string; deduction_type: "fixed" | "percentage"; value: string; active: boolean }>({
    name: rule?.name ?? "",
    description: rule?.description ?? "",
    deduction_type: rule?.deduction_type ?? "fixed",
    value: rule?.value?.toString() ?? "",
    active: rule?.active ?? true,
  });
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.value) return;
    const d: Record<string, unknown> = {
      name: form.name,
      value: Number(form.value),
      deduction_type: form.deduction_type,
      active: form.active,
    };
    if (form.description) d.description = form.description;
    onSubmit(d as DeductionRuleCreate | DeductionRuleUpdate);
    if (!rule) {
      setForm({ name: "", description: "", deduction_type: "fixed", value: "", active: true });
    }
  };
  const upd = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>{rule ? "Edit Deduction Rule" : "Add Deduction Rule"}</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="dr-name">Rule Name</Label>
            <Input id="dr-name" value={form.name} onChange={(e) => upd("name", e.target.value)} required placeholder="e.g. Federal Income Tax" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dr-desc">Description</Label>
            <Input id="dr-desc" value={form.description} onChange={(e) => upd("description", e.target.value)} placeholder="Optional description" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="dr-type">Type</Label>
              <Select value={form.deduction_type} onValueChange={(v: "fixed" | "percentage") => upd("deduction_type", v)}>
                <SelectTrigger id="dr-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="fixed">Fixed Amount</SelectItem>
                  <SelectItem value="percentage">Percentage</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dr-val">Value</Label>
              <Input id="dr-val" type="number" step="0.01" min="0" value={form.value} onChange={(e) => upd("value", e.target.value)} required placeholder={form.deduction_type === "percentage" ? "10" : "500"} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="dr-active">Active</Label>
            <Select value={form.active ? "true" : "false"} onValueChange={(v) => upd("active", v === "true")}>
              <SelectTrigger id="dr-active"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Active</SelectItem>
                <SelectItem value="false">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancel</Button></DialogClose>
            <Button type="submit">{rule ? "Save Changes" : "Create Rule"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Deduction Rules Component ─────────────────────────────────────────────

export function DeductionRules() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [debounced, setDebounced] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<DeductionRuleOut | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<DeductionRuleOut | null>(null);

  useEffect(() => { const t = setTimeout(() => setDebounced(search), 300); return () => clearTimeout(t); }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: ["deduction-rules", { page, pageSize, search: debounced, active_only: activeFilter }],
    queryFn: () => listDeductionRules({
      page, page_size: pageSize, search: debounced || undefined,
      active_only: activeFilter ? (activeFilter === "active") : undefined,
    }),
  });

  const mCreate = useMutation({
    mutationFn: createDeductionRule,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deduction-rules"] }); setFormOpen(false); toast.success("Deduction rule created"); },
  });
  const mUpdate = useMutation({
    mutationFn: ({ id, data }: { id: number; data: DeductionRuleUpdate }) => updateDeductionRule(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deduction-rules"] }); setFormOpen(false); setEditing(null); toast.success("Deduction rule updated"); },
  });
  const mDelete = useMutation({
    mutationFn: deleteDeductionRule,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deduction-rules"] }); setConfirmDelete(null); toast.success("Deduction rule deleted"); },
  });

  const rules = data?.items ?? [];
  const totalPages = data?.total_pages ?? 0;
  const totalRules = data?.total ?? 0;
  const activeCount = rules.filter((r) => r.active).length;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Total Rules</p><p className="text-2xl font-bold">{totalRules}</p></div>
              <div className="p-3 rounded-lg bg-purple-50"><Settings2 className="h-5 w-5 text-purple-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Active</p><p className="text-2xl font-bold">{activeCount}</p></div>
              <div className="p-3 rounded-lg bg-green-50"><Settings2 className="h-5 w-5 text-green-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Fixed</p><p className="text-2xl font-bold">{rules.filter((r) => r.deduction_type === "fixed").length}</p></div>
              <div className="p-3 rounded-lg bg-blue-50"><Settings2 className="h-5 w-5 text-blue-600" /></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted-foreground">Percentage</p><p className="text-2xl font-bold">{rules.filter((r) => r.deduction_type === "percentage").length}</p></div>
              <div className="p-3 rounded-lg bg-orange-50"><Settings2 className="h-5 w-5 text-orange-600" /></div>
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
              <Input placeholder="Search rules…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="pl-10" />
            </div>
            <Select value={activeFilter} onValueChange={(v) => { setActiveFilter(v); setPage(1); }}>
              <SelectTrigger className="w-full sm:w-[160px]"><SelectValue placeholder="All rules" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Rules</SelectItem>
                <SelectItem value="active">Active Only</SelectItem>
                <SelectItem value="inactive">Inactive Only</SelectItem>
              </SelectContent>
            </Select>
            {isAdmin && (
              <Button onClick={() => { setEditing(null); setFormOpen(true); }}>
                <Plus className="h-4 w-4 mr-2" />Add Rule
              </Button>
            )}
          </div>

          {/* Table */}
          <div className="mt-4">
            {isLoading ? (
              <p className="py-8 text-center text-muted-foreground">Loading deduction rules…</p>
            ) : rules.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">No deduction rules found. Add rules to configure payroll calculations.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-medium">{rule.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {rule.deduction_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">{formatValue(rule)}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={rule.active ? "default" : "secondary"} className={rule.active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}>
                          {rule.active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(rule.updated_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {isAdmin && (
                            <>
                              <Button size="sm" variant="ghost" onClick={() => { setEditing(rule); setFormOpen(true); }} title="Edit">
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(rule)} title="Delete">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </>
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
                  Page {page} of {totalPages} ({totalRules} total)
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

      {/* Create/Edit Dialog */}
      <RuleFormDialog
        open={formOpen}
        onOpenChange={(o) => { setFormOpen(o); if (!o) setEditing(null); }}
        rule={editing}
        onSubmit={(d) => {
          if (editing) mUpdate.mutate({ id: editing.id, data: d as DeductionRuleUpdate });
          else mCreate.mutate(d as DeductionRuleCreate);
        }}
      />

      {/* Delete Confirmation */}
      {confirmDelete && (
        <AlertDialog open={!!confirmDelete} onOpenChange={(o) => { if (!o) setConfirmDelete(null); }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Deduction Rule</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete "{confirmDelete.name}"? This will affect future payroll calculations.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => mDelete.mutate(confirmDelete.id)} className="bg-red-600 hover:bg-red-700">
                Delete Rule
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}