import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, Plus, Target, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getMyProfile, listEmployees, type Employee } from "@/lib/employee";
import {
  createGoal,
  deleteGoal,
  listGoals,
  updateGoal,
  type Goal,
  type GoalStatus,
} from "@/lib/goals";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";

/** Extract a human message from an axios error (detail may be a string or {code, message}). */
function errMsg(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (
    d &&
    typeof d === "object" &&
    "message" in d &&
    typeof (d as { message: unknown }).message === "string"
  ) {
    return (d as { message: string }).message;
  }
  return "Something went wrong. Please try again.";
}

export function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "—";
  }
}

/* ------------------------------------------------------------------ */
/*  Status badge + progress bar                                        */
/* ------------------------------------------------------------------ */

export function GoalStatusBadge({ status }: { status: GoalStatus }) {
  if (status === "completed")
    return (
      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700">
        <Check className="mr-1 h-3 w-3" />
        Completed
      </Badge>
    );
  if (status === "archived") return <Badge variant="outline">Archived</Badge>;
  return <Badge variant="default">Active</Badge>;
}

function ProgressBar({ value, status }: { value: number; status: GoalStatus }) {
  const color =
    status === "completed"
      ? "bg-emerald-500"
      : status === "archived"
        ? "bg-gray-300"
        : "bg-blue-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">{value}%</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  GoalFormDialog: create a goal or edit an existing one              */
/* ------------------------------------------------------------------ */

interface GoalFormProps {
  /** Employees the current user may set a goal for (pre-filtered by role). */
  candidates: Employee[];
  editing: Goal | null;
  defaultEmployeeId?: number;
  onClose: () => void;
  onSaved: () => void;
}

function GoalFormDialog({
  candidates,
  editing,
  defaultEmployeeId,
  onClose,
  onSaved,
}: GoalFormProps) {
  const initialEmployee = editing
    ? String(editing.employee_id)
    : String(defaultEmployeeId ?? candidates[0]?.id ?? "");

  const [employeeId, setEmployeeId] = useState(initialEmployee);
  const [title, setTitle] = useState(editing?.title ?? "");
  const [period, setPeriod] = useState(editing?.period ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [progress, setProgress] = useState(editing?.progress ?? 0);
  const [status, setStatus] = useState<GoalStatus>(editing?.status ?? "active");
  const [error, setError] = useState<string | null>(null);

  const canPickEmployee = !editing;

  const mSave = useMutation({
    mutationFn: () => {
      const payload = {
        title: title.trim(),
        period: period.trim(),
        description: description.trim() || null,
        progress,
      };
      if (editing) {
        return updateGoal(editing.id, { ...payload, status });
      }
      return createGoal({ employee_id: Number(employeeId), ...payload });
    },
    onSuccess: () => {
      onSaved();
      toast.success(editing ? "Goal updated" : "Goal created");
      onClose();
    },
    onError: (e) => setError(errMsg(e)),
  });

  const valid =
    title.trim().length >= 3 && period.trim().length >= 2 && (!canPickEmployee || employeeId);

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit goal" : "New goal"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Update the details, progress, or status of this goal."
              : "Set an objective for an employee for a labeled period."}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (valid) mSave.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label>Employee</Label>
            {canPickEmployee ? (
              <Select value={employeeId} onValueChange={setEmployeeId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an employee" />
                </SelectTrigger>
                <SelectContent>
                  {candidates.length === 0 && (
                    <SelectItem value="" disabled>
                      No eligible employees
                    </SelectItem>
                  )}
                  {candidates.map((emp) => (
                    <SelectItem key={emp.id} value={String(emp.id)}>
                      {emp.first_name} {emp.last_name}
                      {emp.position ? ` — ${emp.position}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
                <span className="font-medium">{editing?.employee_name}</span>
                {editing?.employee_position && (
                  <span className="ml-2 text-muted-foreground">
                    {editing.employee_position}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="goal-title">Title</Label>
            <Input
              id="goal-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Ship the Q3 reporting dashboard"
              maxLength={150}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="goal-period">Period</Label>
              <Input
                id="goal-period"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                placeholder="e.g. H2 2026"
                maxLength={20}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="goal-progress">Progress</Label>
              <Input
                id="goal-progress"
                type="number"
                min={0}
                max={100}
                value={progress}
                onChange={(e) =>
                  setProgress(
                    Math.min(100, Math.max(0, Number(e.target.value) || 0))
                  )
                }
              />
            </div>
          </div>

          {editing && (
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={status} onValueChange={(v) => setStatus(v as GoalStatus)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="goal-description">Description</Label>
            <Textarea
              id="goal-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does success look like, and why does it matter?"
              maxLength={4000}
            />
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={mSave.isPending || !valid}>
              {editing ? "Save changes" : "Create goal"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  GoalsPage — role-aware OKR board (admin / manager / employee)      */
/* ------------------------------------------------------------------ */

/**
 * Goals page, shared by all roles — the server scopes the list:
 * admins see every goal, managers their own + direct reports', employees
 * their own (where the page renders as "My Goals"). Every goal shown to a
 * role is editable by that role; deleting is stricter (owner or admin).
 */
export default function GoalsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const role = user?.role ?? "employee";
  const isAdmin = role === "admin";
  const isManager = role === "manager";

  const [statusFilter, setStatusFilter] = useState<GoalStatus | "">("");
  const [periodFilter, setPeriodFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [deleting, setDeleting] = useState<Goal | null>(null);

  // Linked employee profile. Admins may have none — that's fine; an
  // employee role without one has no goals to show.
  const meQ = useQuery({
    queryKey: ["my-profile"],
    queryFn: getMyProfile,
  });
  const me = meQ.data ?? null;
  const meId = me?.id ?? null;

  // Full roster — needed for the "new goal" picker and manager scoping.
  const rosterQ = useQuery({
    queryKey: ["employees", "goal-candidates"],
    queryFn: async () => {
      const r = await listEmployees({ page: 1, page_size: 100 });
      return r.data.items;
    },
    enabled: isAdmin || isManager,
  });

  const goalsQ = useQuery({
    queryKey: ["goals", statusFilter, periodFilter],
    queryFn: () =>
      listGoals({
        status: statusFilter || undefined,
        period: periodFilter.trim() || undefined,
      }),
    // Profile-less employees would get a 403 — show a friendly card instead.
    enabled: isAdmin || isManager || !!me,
  });

  const goals = goalsQ.data ?? [];

  /** Employees the current user may set a goal for. */
  const candidates = useMemo(() => {
    const active = (rosterQ.data ?? []).filter((e) => e.status === "active");
    if (isAdmin) return active;
    if (isManager) return active.filter((e) => e.id === meId || e.manager_id === meId);
    return me ? [me] : [];
  }, [isAdmin, isManager, rosterQ.data, me, meId]);

  const mDelete = useMutation({
    mutationFn: deleteGoal,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      toast.success("Goal deleted");
      setDeleting(null);
    },
    onError: (e) => toast.error("Couldn't delete the goal", errMsg(e)),
  });

  const handleSaved = () => {
    qc.invalidateQueries({ queryKey: ["goals"] });
  };

  const notLinked = role === "employee" && !meQ.isLoading && !me;

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {isAdmin || isManager ? "Goals" : "My Goals"}
          </h1>
          <p className="text-muted-foreground mt-1">
            {isAdmin
              ? "Objectives and progress across the whole company."
              : isManager
                ? "Objectives for you and your direct reports."
                : "Your objectives and progress, period by period."}
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New goal
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <Select
              value={statusFilter || "all"}
              onValueChange={(v) =>
                setStatusFilter(v === "all" ? "" : (v as GoalStatus))
              }
            >
              <SelectTrigger className="w-[170px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
            <Input
              className="w-[210px]"
              placeholder="Filter by period (e.g. H2 2026)"
              value={periodFilter}
              onChange={(e) => setPeriodFilter(e.target.value)}
            />
            <p className="ml-auto text-sm tabular-nums text-muted-foreground">
              {goals.length} {goals.length === 1 ? "goal" : "goals"}
            </p>
          </div>

          <div className="mt-4">
            {notLinked ? (
              <div className="rounded-lg bg-muted/40 px-4 py-6 text-center text-sm text-muted-foreground">
                <p className="font-medium text-foreground">
                  Your account isn't linked to an employee record yet.
                </p>
                <p className="mt-1">
                  Contact HR to connect your login with your profile.
                </p>
              </div>
            ) : goalsQ.isLoading ? (
              <div className="flex justify-center py-10 text-sm text-muted-foreground">
                Loading…
              </div>
            ) : goalsQ.isError ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center text-sm text-red-700">
                {errMsg(goalsQ.error)}
              </div>
            ) : goals.length === 0 ? (
              <div className="py-10 text-center">
                <Target className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-3 font-medium">
                  {statusFilter || periodFilter ? "No goals match these filters" : "No goals yet"}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {statusFilter || periodFilter
                    ? "Try a different status or period."
                    : "Create the first goal to start tracking progress."}
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[180px]">Employee</TableHead>
                    <TableHead>Goal</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Progress</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[110px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {goals.map((g) => (
                    <TableRow key={g.id}>
                      <TableCell>
                        <div className="font-medium text-gray-900">{g.employee_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {[g.employee_department, g.employee_position]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[300px]">
                        <div className="font-medium">{g.title}</div>
                        {g.description && (
                          <div className="mt-0.5 truncate text-xs text-muted-foreground">
                            {g.description}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{g.period}</TableCell>
                      <TableCell>
                        <ProgressBar value={g.progress} status={g.status} />
                      </TableCell>
                      <TableCell>
                        <GoalStatusBadge status={g.status} />
                        {g.completed_at && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            Done {formatDate(g.completed_at)}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="Edit goal"
                            onClick={() => setEditing(g)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          {(isAdmin || g.employee_id === meId) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-600 hover:text-red-700"
                              title="Delete goal"
                              onClick={() => setDeleting(g)}
                            >
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
          </div>
        </CardContent>
      </Card>

      {(creating || editing) && (
        <GoalFormDialog
          candidates={candidates}
          editing={editing}
          defaultEmployeeId={meId ?? undefined}
          onClose={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSaved={handleSaved}
        />
      )}

      <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this goal?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleting?.title}” ({deleting?.period}) will be permanently
              removed. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 text-white hover:bg-red-700"
              onClick={(e) => {
                // Keep the dialog open until the delete actually succeeds.
                e.preventDefault();
                if (deleting) mDelete.mutate(deleting.id);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
