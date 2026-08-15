import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, Check, Clock, Eye, Pencil, Plus, Send, Share2, Star } from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  createReview,
  createReviewCycle,
  listCycleReviews,
  listReviewCycles,
  shareReview,
  updateReview,
  type Review,
  type ReviewCycle,
} from "@/lib/review";
import { getMyProfile, listEmployees, type Employee } from "@/lib/employee";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";

export function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

/** Extract a human message from an axios error (detail may be a string or {code, message}). */
function errMsg(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && "message" in d && typeof (d as { message: unknown }).message === "string") {
    return (d as { message: string }).message;
  }
  return "Something went wrong. Please try again.";
}

/* ------------------------------------------------------------------ */
/*  Stars: read-only rating display                                     */
/* ------------------------------------------------------------------ */

export function Stars({ rating, size = "md" }: { rating: number | null; size?: "sm" | "md" }) {
  const cls = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`${cls} ${rating != null && n <= rating ? "fill-amber-400 text-amber-400" : "text-gray-300"}`}
        />
      ))}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  StarInput: clickable 1–5 rating picker                              */
/* ------------------------------------------------------------------ */

function StarInput({ value, onChange }: { value: number | null; onChange: (v: number | null) => void }) {
  const [hover, setHover] = useState<number | null>(null);
  const shown = hover ?? value ?? 0;
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(null)}
          onClick={() => onChange(value === n ? null : n)}
          className="rounded p-0.5 transition-colors hover:bg-amber-50"
          aria-label={`Rate ${n} out of 5`}
        >
          <Star
            className={`h-6 w-6 transition-colors ${
              shown >= n ? "fill-amber-400 text-amber-400" : "text-gray-300"
            }`}
          />
        </button>
      ))}
      <span className="ml-2 text-sm text-muted-foreground">
        {value != null ? `${value} / 5` : "No rating"}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ReviewStatusBadge                                                   */
/* ------------------------------------------------------------------ */

export function ReviewStatusBadge({ status }: { status: Review["status"] }) {
  if (status === "shared")
    return (
      <Badge variant="default">
        <Check className="mr-1 h-3 w-3" />
        Shared
      </Badge>
    );
  if (status === "submitted")
    return (
      <Badge variant="secondary">
        <Send className="mr-1 h-3 w-3" />
        Submitted
      </Badge>
    );
  return (
    <Badge variant="outline">
      <Clock className="mr-1 h-3 w-3" />
      Draft
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  CycleCard: one review cycle with live progress                      */
/* ------------------------------------------------------------------ */

function CycleCard({
  cycle,
  selected,
  onSelect,
}: {
  cycle: ReviewCycle;
  selected: boolean;
  onSelect: () => void;
}) {
  const total = cycle.total_reviews;
  const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`text-left rounded-xl border bg-white p-4 transition-all ${
        selected
          ? "border-blue-500 ring-2 ring-blue-500/20 shadow-sm"
          : "border-gray-200 hover:border-blue-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold text-gray-900">{cycle.name}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatDate(cycle.period_start)} – {formatDate(cycle.period_end)}
          </p>
        </div>
        <Badge variant={cycle.status === "active" ? "default" : "secondary"}>
          {cycle.status === "active" ? "Active" : "Closed"}
        </Badge>
      </div>

      <div className="mt-3">
        <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
          {total > 0 && (
            <>
              <div className="bg-amber-400" style={{ width: `${pct(cycle.drafts)}%` }} />
              <div className="bg-blue-500" style={{ width: `${pct(cycle.submitted)}%` }} />
              <div className="bg-emerald-500" style={{ width: `${pct(cycle.shared)}%` }} />
            </>
          )}
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            {cycle.drafts} draft{cycle.drafts === 1 ? "" : "s"}
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            {cycle.submitted} submitted
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            {cycle.shared} shared
          </span>
        </div>
      </div>

      {cycle.description && (
        <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{cycle.description}</p>
      )}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  ReviewFormDialog: create a new review or edit a draft               */
/* ------------------------------------------------------------------ */

interface ReviewFormProps {
  cycle: ReviewCycle;
  /** Employees the current user may review (pre-filtered by role). */
  candidates: Employee[];
  /** Employee ids that already have a review in this cycle. */
  reviewedIds: Set<number>;
  editing: Review | null;
  onClose: () => void;
  onSaved: () => void;
}

function ReviewFormDialog({
  cycle,
  candidates,
  reviewedIds,
  editing,
  onClose,
  onSaved,
}: ReviewFormProps) {
  const [employeeId, setEmployeeId] = useState<string>(editing ? String(editing.employee_id) : "");
  const [rating, setRating] = useState<number | null>(editing?.rating ?? null);
  const [strengths, setStrengths] = useState(editing?.strengths ?? "");
  const [improvements, setImprovements] = useState(editing?.improvements ?? "");
  const [goals, setGoals] = useState(editing?.goals ?? "");
  const [error, setError] = useState<string | null>(null);

  const mSave = useMutation({
    mutationFn: (submit: boolean) => {
      const payload = {
        rating,
        strengths: strengths.trim() || null,
        improvements: improvements.trim() || null,
        goals: goals.trim() || null,
      };
      if (editing) {
        return updateReview(editing.id, { ...payload, status: submit ? ("submitted" as const) : undefined });
      }
      return createReview(cycle.id, { employee_id: Number(employeeId), ...payload, submit: submit });
    },
    onSuccess: () => {
      onSaved();
      toast.success(editing ? "Review updated" : "Review created");
      onClose();
    },
    onError: (e) => setError(errMsg(e)),
  });

  const remaining = candidates.filter((c) => !reviewedIds.has(c.id));

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit review" : "New review"}</DialogTitle>
          <DialogDescription>
            {cycle.name} · {formatDate(cycle.period_start)} – {formatDate(cycle.period_end)}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            mSave.mutate(true);
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label>Employee</Label>
            {editing ? (
              <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
                <span className="font-medium">{editing.employee_name}</span>
                {editing.employee_position && (
                  <span className="ml-2 text-muted-foreground">{editing.employee_position}</span>
                )}
              </div>
            ) : (
              <Select value={employeeId} onValueChange={setEmployeeId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an employee" />
                </SelectTrigger>
                <SelectContent>
                  {remaining.length === 0 && (
                    <SelectItem value="" disabled>
                      Every eligible employee has been reviewed
                    </SelectItem>
                  )}
                  {remaining.map((emp) => (
                    <SelectItem key={emp.id} value={String(emp.id)}>
                      {emp.first_name} {emp.last_name}
                      {emp.position ? ` — ${emp.position}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="space-y-2">
            <Label>Overall rating</Label>
            <StarInput value={rating} onChange={setRating} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="strengths">What they did well</Label>
            <Textarea
              id="strengths"
              rows={3}
              value={strengths}
              onChange={(e) => setStrengths(e.target.value)}
              placeholder="Key accomplishments, strengths, and impact this period…"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="improvements">Areas to improve</Label>
            <Textarea
              id="improvements"
              rows={3}
              value={improvements}
              onChange={(e) => setImprovements(e.target.value)}
              placeholder="Skills to develop or goals to focus on next…"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="goals">Goals for next period</Label>
            <Textarea
              id="goals"
              rows={3}
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              placeholder="Concrete goals to work toward…"
            />
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              disabled={mSave.isPending || (!editing && !employeeId)}
              onClick={() => mSave.mutate(false)}
            >
              {editing ? "Save changes" : "Save as draft"}
            </Button>
            <Button type="submit" disabled={mSave.isPending || (!editing && !employeeId)}>
              <Send className="mr-2 h-4 w-4" />
              {editing ? "Mark as submitted" : "Submit review"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  ReviewDetailDialog: read-only view + submit / share actions        */
/* ------------------------------------------------------------------ */

function ReviewDetailDialog({
  review,
  canModify,
  onClose,
  onEdit,
  onSubmitted,
  onShared,
}: {
  review: Review;
  canModify: boolean;
  onClose: () => void;
  onEdit: () => void;
  onSubmitted: () => void;
  onShared: () => void;
}) {
  const mSubmit = useMutation({
    mutationFn: () => updateReview(review.id, { status: "submitted" }),
    onSuccess: () => {
      toast.success("Review submitted");
      onSubmitted();
      onClose();
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const mShare = useMutation({
    mutationFn: () => shareReview(review.id),
    onSuccess: () => {
      toast.success("Review shared with the employee");
      onShared();
      onClose();
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const Section = ({ label, value }: { label: string; value: string | null }) => (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm text-gray-800">{value || "—"}</p>
    </div>
  );

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center justify-between gap-2">
            <DialogTitle>{review.employee_name}</DialogTitle>
            <ReviewStatusBadge status={review.status} />
          </div>
          <DialogDescription>
            {review.cycle_name} · {review.employee_position ?? "Employee"}
            {review.employee_department ? ` · ${review.employee_department}` : ""}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg bg-amber-50/60 px-4 py-3">
            <span className="text-sm font-medium text-gray-700">Overall rating</span>
            <div className="flex items-center gap-2">
              <Stars rating={review.rating} />
              <span className="text-sm font-semibold tabular-nums">
                {review.rating != null ? `${review.rating}/5` : "—"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Section label="What they did well" value={review.strengths} />
            <Section label="Areas to improve" value={review.improvements} />
            <Section label="Goals for next period" value={review.goals} />
            <div className="space-y-1 text-xs text-muted-foreground">
              <p>Reviewed by {review.reviewer_name ?? "—"}</p>
              {review.submitted_at && <p>Submitted {formatDate(review.submitted_at)}</p>}
              {review.shared_at && <p>Shared {formatDate(review.shared_at)}</p>}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          {review.status === "shared" && (
            <p className="w-full text-center text-xs text-muted-foreground sm:w-auto sm:text-right">
              Shared — the employee can see this review.
            </p>
          )}
          {canModify && review.status === "draft" && (
            <>
              <Button variant="outline" onClick={onEdit}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </Button>
              <Button onClick={() => mSubmit.mutate()} disabled={mSubmit.isPending}>
                <Send className="mr-2 h-4 w-4" />
                Submit
              </Button>
            </>
          )}
          {canModify && review.status === "submitted" && (
            <Button onClick={() => mShare.mutate()} disabled={mShare.isPending}>
              <Share2 className="mr-2 h-4 w-4" />
              Share with employee
            </Button>
          )}
          {!canModify && (
            <p className="w-full text-center text-xs text-muted-foreground sm:w-auto sm:text-right">
              Read-only — only the author or an admin can change this review.
            </p>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  CycleDialog: admin creates a new review cycle                       */
/* ------------------------------------------------------------------ */

function CycleDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (c: ReviewCycle) => void }) {
  const year = new Date().getFullYear();
  const [name, setName] = useState("");
  const [start, setStart] = useState(`${year}-01-01`);
  const [end, setEnd] = useState(`${year}-12-31`);
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mCreate = useMutation({
    mutationFn: () =>
      createReviewCycle({
        name: name.trim(),
        period_start: start,
        period_end: end,
        description: description.trim() || undefined,
      }),
    onSuccess: (cycle) => {
      toast.success("Review cycle created");
      onCreated(cycle);
      onClose();
    },
    onError: (e) => setError(errMsg(e)),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New review cycle</DialogTitle>
          <DialogDescription>
            A cycle is one review period — managers write one review per employee in it.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mCreate.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="cycle-name">Cycle name</Label>
            <Input
              id="cycle-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. 2026 Mid-Year Review"
              required
              minLength={3}
              maxLength={100}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cycle-start">Period start</Label>
              <Input id="cycle-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cycle-end">Period end</Label>
              <Input id="cycle-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="cycle-desc">Description (optional)</Label>
            <Textarea
              id="cycle-desc"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What should reviewers focus on this period?"
            />
          </div>
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={mCreate.isPending || !name.trim()}>
              <Plus className="mr-2 h-4 w-4" />
              Create cycle
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  PerformancePage: cycles + reviews for managers and admins         */
/* ------------------------------------------------------------------ */

export default function PerformancePage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isAdmin = user?.role === "admin";

  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCycleDialog, setShowCycleDialog] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Review | null>(null);
  const [detail, setDetail] = useState<Review | null>(null);

  const { data: cycles, isLoading } = useQuery({
    queryKey: ["review-cycles"],
    queryFn: listReviewCycles,
  });

  const activeCycle = cycles?.find((c) => c.status === "active");
  const cycle =
    cycles?.find((c) => c.id === selectedCycleId) ?? activeCycle ?? cycles?.[0] ?? null;

  const { data: reviews, isPending: reviewsLoading } = useQuery({
    queryKey: ["review-cycles", cycle?.id, "reviews"],
    queryFn: () => listCycleReviews(cycle!.id),
    enabled: !!cycle,
  });

  // Employees the current user may review: admins can review anyone,
  // managers only their direct reports (mirrors the backend rule; the
  // API still enforces it authoritatively).
  const { data: empData } = useQuery({
    queryKey: ["employees", "performance-candidates"],
    // Backend caps page_size at 100 — more than enough for the candidate list.
    queryFn: () => listEmployees({ page: 1, page_size: 100, status: "active" }),
  });
  const { data: me } = useQuery({
    queryKey: ["my-profile"],
    queryFn: getMyProfile,
    retry: false,
  });
  const candidates: Employee[] = useMemo(() => {
    const all = empData?.data.items ?? [];
    if (user?.role === "manager" && me) {
      return all.filter((e) => e.manager_id === me.id);
    }
    return all;
  }, [empData, me, user?.role]);

  const reviewedIds = useMemo(
    () => new Set((reviews ?? []).map((r) => r.employee_id)),
    [reviews]
  );

  const canModify = (r: Review) =>
    user != null && (r.reviewer_user_id === user.id || user.role === "admin");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["review-cycles"] });

  const mSubmit = useMutation({
    mutationFn: (id: number) => updateReview(id, { status: "submitted" }),
    onSuccess: () => {
      invalidate();
      toast.success("Review submitted");
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const mShare = useMutation({
    mutationFn: (id: number) => shareReview(id),
    onSuccess: () => {
      invalidate();
      toast.success("Review shared with the employee");
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const filtered = (reviews ?? []).filter(
    (r) => !statusFilter || r.status === statusFilter
  );

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Performance Reviews</h1>
          <p className="text-muted-foreground mt-1">
            Run review cycles, write evaluations, and share them with your team.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {cycle?.status === "active" && (
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              New review
            </Button>
          )}
          {isAdmin && (
            <Button variant="outline" onClick={() => setShowCycleDialog(true)}>
              <Award className="h-4 w-4 mr-2" />
              New cycle
            </Button>
          )}
        </div>
      </div>

      {/* Cycles */}
      {isLoading ? (
        <div className="flex justify-center py-8 text-muted-foreground">Loading…</div>
      ) : cycles && cycles.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cycles.map((c) => (
            <CycleCard
              key={c.id}
              cycle={c}
              selected={cycle?.id === c.id}
              onSelect={() => {
                setSelectedCycleId(c.id);
                setStatusFilter("");
              }}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10 text-center">
            <Award className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 font-medium">No review cycles yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {isAdmin
                ? "Create a cycle to get started."
                : "An admin has not created a review cycle yet."}
            </p>
            {isAdmin && (
              <Button className="mt-4" onClick={() => setShowCycleDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create cycle
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Reviews in the selected cycle */}
      {cycle && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-lg">
              {cycle.name}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {reviews?.length ?? 0} review{(reviews?.length ?? 0) === 1 ? "" : "s"}
              </span>
            </CardTitle>
            <div className="flex items-center gap-2">
              <Select
                value={statusFilter}
                onValueChange={(v) => setStatusFilter(v || "")}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Statuses</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="submitted">Submitted</SelectItem>
                  <SelectItem value="shared">Shared</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {reviewsLoading ? (
              <div className="flex justify-center py-8 text-muted-foreground">Loading…</div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-muted-foreground gap-2">
                <Award className="h-10 w-10 opacity-40" />
                <p>
                  {statusFilter
                    ? `No ${statusFilter} reviews in this cycle`
                    : "No reviews in this cycle yet"}
                </p>
                {cycle.status === "active" && !statusFilter && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditing(null);
                      setFormOpen(true);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Write the first review
                  </Button>
                )}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Employee</TableHead>
                    <TableHead>Rating</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Reviewer</TableHead>
                    <TableHead>Submitted</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <p className="font-medium">{r.employee_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {[r.employee_position, r.employee_department]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </p>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Stars rating={r.rating} size="sm" />
                          <span className="text-xs tabular-nums text-muted-foreground">
                            {r.rating != null ? r.rating : "—"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <ReviewStatusBadge status={r.status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {r.reviewer_name ?? "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(r.submitted_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          {canModify(r) && r.status === "draft" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Edit draft"
                              disabled={mSubmit.isPending}
                              onClick={() => {
                                setDetail(null);
                                setEditing(r);
                                setFormOpen(true);
                              }}
                            >
                              <Pencil className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          )}
                          {canModify(r) && r.status === "draft" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Submit"
                              disabled={mSubmit.isPending}
                              onClick={() => mSubmit.mutate(r.id)}
                            >
                              <Send className="h-4 w-4 text-blue-600" />
                            </Button>
                          )}
                          {canModify(r) && r.status === "submitted" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Share with employee"
                              disabled={mShare.isPending}
                              onClick={() => mShare.mutate(r.id)}
                            >
                              <Share2 className="h-4 w-4 text-emerald-600" />
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            title="View details"
                            onClick={() => setDetail(r)}
                          >
                            <Eye className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Dialogs */}
      {showCycleDialog && (
        <CycleDialog
          onClose={() => setShowCycleDialog(false)}
          onCreated={(c) => setSelectedCycleId(c.id)}
        />
      )}

      {formOpen && cycle && (
        <ReviewFormDialog
          cycle={cycle}
          candidates={candidates}
          reviewedIds={reviewedIds}
          editing={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      )}

      {detail && (
        <ReviewDetailDialog
          review={detail}
          canModify={canModify(detail)}
          onClose={() => setDetail(null)}
          onEdit={() => {
            setDetail(null);
            setEditing(detail);
            setFormOpen(true);
          }}
          onSubmitted={() => {
            invalidate();
          }}
          onShared={() => {
            invalidate();
          }}
        />
      )}
    </div>
  );
}




