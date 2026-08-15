import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Clock, LogIn, LogOut, CalendarDays, TrendingUp, Hourglass } from "lucide-react";
import {
  getMyMonthAttendance,
  recordTime,
  nowClockTime,
  toDateInput,
  formatClock,
  formatWorkDate,
  type MonthParams,
} from "@/lib/attendance";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/hooks/use-toast";

/** The 12 most recent months (newest first) for the month selector. */
function lastTwelveMonths(now: Date): { year: number; month: number }[] {
  const out: { year: number; month: number }[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    out.push({ year: d.getFullYear(), month: d.getMonth() + 1 });
  }
  return out;
}

function monthLabel(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function StatCard({ title, value, sub, icon, bgColor }: {
  title: string; value: string; sub?: string; icon: React.ReactNode; bgColor: string;
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
          <div className={`p-3 rounded-lg ${bgColor}`}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function MyTimePage() {
  const qc = useQueryClient();
  const today = new Date();
  const todayStr = toDateInput(today);
  const months = useMemo(() => lastTwelveMonths(today), []);
  const [sel, setSel] = useState(`${today.getFullYear()}-${today.getMonth() + 1}`);
  const [year, month] = sel.split("-").map(Number);
  const isCurrentMonth = year === today.getFullYear() && month === today.getMonth() + 1;

  const params: MonthParams = { year, month };
  const { data: monthData, isLoading } = useQuery({
    queryKey: ["my-attendance", params],
    queryFn: () => getMyMonthAttendance(params),
  });

  const todayEntry = monthData?.items.find((e) => e.work_date === todayStr) ?? null;

  const clockMutation = useMutation({
    mutationFn: (action: "in" | "out") => {
      const payload =
        action === "in"
          ? { work_date: todayStr, clock_in: nowClockTime() }
          : { work_date: todayStr, clock_in: todayEntry!.clock_in, clock_out: nowClockTime() };
      return recordTime(payload);
    },
    onSuccess: (_, action) => {
      qc.invalidateQueries({ queryKey: ["my-attendance"] });
      toast.success(action === "in" ? "Clocked in" : "Clocked out");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail?.message ?? "Could not record time");
    },
  });

  const items = [...(monthData?.items ?? [])].sort((a, b) => b.work_date.localeCompare(a.work_date));

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Time</h1>
          <p className="text-muted-foreground mt-1">
            Clock in and out each day, and review your recorded hours.
          </p>
        </div>
        <div className="w-44">
          <Select value={sel} onValueChange={setSel}>
            <SelectTrigger><SelectValue placeholder="Select month" /></SelectTrigger>
            <SelectContent>
              {months.map((m) => (
                <SelectItem key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
                  {monthLabel(m.year, m.month)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Today card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg">
            Today — {formatWorkDate(todayStr)}
          </CardTitle>
          {todayEntry ? (
            todayEntry.clock_out ? (
              <Badge variant="default">Day closed · {todayEntry.hours?.toFixed(1)}h</Badge>
            ) : (
              <Badge variant="secondary">
                <Hourglass className="mr-1 h-3 w-3" />
                Clock in at {formatClock(todayEntry.clock_in)}
              </Badge>
            )
          ) : (
            <Badge variant="outline">Not clocked in yet</Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          {!isCurrentMonth ? (
            <p className="text-sm text-muted-foreground">
              Select the current month to record today's time.
            </p>
          ) : !todayEntry ? (
            <Button
              onClick={() => clockMutation.mutate("in")}
              disabled={clockMutation.isPending}
            >
              <LogIn className="h-4 w-4 mr-2" />
              Clock In
            </Button>
          ) : todayEntry.clock_out === null ? (
            <div className="flex items-center gap-4">
              <Button
                onClick={() => clockMutation.mutate("out")}
                disabled={clockMutation.isPending}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Clock Out
              </Button>
              <p className="text-sm text-muted-foreground">
                In since {formatClock(todayEntry.clock_in)}
              </p>
            </div>
          ) : (
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>Clock in {formatClock(todayEntry.clock_in)}</span>
              <span>·</span>
              <span>Clock out {formatClock(todayEntry.clock_out)}</span>
              <span>·</span>
              <span>{todayEntry.breaks_minutes}m break</span>
              <span>·</span>
              <span className="font-medium text-foreground">{todayEntry.hours?.toFixed(1)}h</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Month summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          title="Total Hours"
          value={`${monthData?.total_hours ?? 0}h`}
          sub={monthLabel(year, month)}
          icon={<Clock className="h-5 w-5 text-blue-600" />}
          bgColor="bg-blue-50"
        />
        <StatCard
          title="Days Recorded"
          value={String(monthData?.days_recorded ?? 0)}
          sub={monthLabel(year, month)}
          icon={<CalendarDays className="h-5 w-5 text-green-600" />}
          bgColor="bg-green-50"
        />
        <StatCard
          title="Average / Day"
          value={monthData?.avg_daily_hours != null ? `${monthData.avg_daily_hours}h` : "—"}
          sub="Over recorded days"
          icon={<TrendingUp className="h-5 w-5 text-amber-600" />}
          bgColor="bg-amber-50"
        />
      </div>

      {/* Entries table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Entries — {monthLabel(year, month)}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No time recorded this month.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Clock In</TableHead>
                  <TableHead>Clock Out</TableHead>
                  <TableHead>Break</TableHead>
                  <TableHead>Hours</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((e) => (
                  <TableRow key={e.id} className={e.work_date === todayStr ? "bg-muted/40" : ""}>
                    <TableCell className="font-medium">{formatWorkDate(e.work_date)}</TableCell>
                    <TableCell>{formatClock(e.clock_in)}</TableCell>
                    <TableCell>
                      {e.clock_out ? (
                        formatClock(e.clock_out)
                      ) : (
                        <Badge variant="secondary">Open</Badge>
                      )}
                    </TableCell>
                    <TableCell>{e.breaks_minutes > 0 ? `${e.breaks_minutes}m` : "—"}</TableCell>
                    <TableCell className="font-medium">
                      {e.hours != null ? `${e.hours}h` : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{e.notes || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
