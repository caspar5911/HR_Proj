import { useQuery } from "@tanstack/react-query";
import { Award, Check, Clock, Inbox, Send } from "lucide-react";
import { listCycleReviews, listReviewCycles, type Review, type ReviewCycle } from "@/lib/review";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Stars, ReviewStatusBadge, formatDate } from "./performance";

interface CycleBlock {
  cycle: ReviewCycle;
  reviews: Review[];
}

/**
 * "My Reviews" — the employee's view of reviews written about them,
 * grouped by cycle. The API returns only this user's reviews, so no
 * client-side filtering is needed.
 */
export default function MyReviewsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-reviews"],
    queryFn: async (): Promise<CycleBlock[]> => {
      const cycles = await listReviewCycles();
      const lists = await Promise.all(cycles.map((c) => listCycleReviews(c.id)));
      return cycles.map((cycle, i) => ({ cycle, reviews: lists[i] }));
    },
  });

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">My Reviews</h1>
        <p className="text-muted-foreground mt-1">
          Feedback from your manager, one card per review cycle.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10 text-muted-foreground">Loading…</div>
      ) : data && data.length > 0 ? (
        <div className="space-y-6">
          {data.map(({ cycle, reviews }) => (
            <Card key={cycle.id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-lg">{cycle.name}</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {formatDate(cycle.period_start)} – {formatDate(cycle.period_end)}
                  </p>
                </div>
                <Badge variant={cycle.status === "active" ? "default" : "secondary"}>
                  {cycle.status === "active" ? "Active cycle" : "Closed cycle"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                {reviews.length === 0 ? (
                  <div className="flex items-center gap-3 rounded-lg bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4 shrink-0" />
                    {cycle.status === "active"
                      ? "Your manager hasn't written your review for this cycle yet."
                      : "No review was written for this cycle."}
                  </div>
                ) : (
                  reviews.map((r) => <ReviewCard key={r.id} review={r} />)
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10 text-center">
            <Inbox className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 font-medium">No review cycles yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Once HR opens a review cycle, your manager's feedback will appear here.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-50">
            <Award className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">
              Review by {review.reviewer_name ?? "your manager"}
            </p>
            <p className="text-xs text-muted-foreground">
              {review.submitted_at ? `Submitted ${formatDate(review.submitted_at)}` : "In progress"}
              {review.shared_at ? ` · Shared ${formatDate(review.shared_at)}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Stars rating={review.rating} />
            <span className="text-sm font-semibold tabular-nums">
              {review.rating != null ? `${review.rating}/5` : "—"}
            </span>
          </div>
          <ReviewStatusBadge status={review.status} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Block
          label="What you did well"
          value={review.strengths}
          icon={Check}
          iconCls="bg-emerald-50 text-emerald-600"
        />
        <Block
          label="Areas to improve"
          value={review.improvements}
          icon={Clock}
          iconCls="bg-amber-50 text-amber-600"
        />
        <Block
          label="Goals for next period"
          value={review.goals}
          icon={Send}
          iconCls="bg-blue-50 text-blue-600"
        />
      </div>
    </div>
  );
}

function Block({
  label,
  value,
  icon: Icon,
  iconCls,
}: {
  label: string;
  value: string | null;
  icon: typeof Check;
  iconCls: string;
}) {
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <div className="flex items-center gap-2">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full ${iconCls}`}>
          <Icon className="h-3.5 w-3.5" />
        </span>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm text-gray-800">{value || "—"}</p>
    </div>
  );
}
