import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, CalendarDays, Users, Zap, ChevronRight } from "lucide-react";
import {
  getTeamAttendance,
  getEmployeeMonthAttendance,
  formatClock,
  formatWorkDate,
  type MonthParams,
} from "@/lib/attendance";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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

export default function AttendancePage() {
  const now = new Date();
  const months = useMemo(() => lastTwelveMonths(now), []);
  const [sel, setSel] = useState(`${now.getFullYear()}-${now.getMonth() + 1}`);
  const [year, month] = sel.split("-").map(Number);
  const [selectedEmp, setSelectedEmp] = useState<number | null>(null);

  const params: MonthParams = { year, month };
  const { data: rows, isLoading } = useQuery({
    queryKey: ["team-attendance", params],
    queryFn: () => getTeamAttendance(params),
  });

  const { data: detail } = useQuery({
    queryKey: ["employee-attendance", selectedEmp, params],
    queryFn: () => getEmployeeMonthAttendance(selectedEmp!, params),
    enabled: selectedEmp != null,
  });

  const totalHours = rows?.reduce((s, r) => s + r.total_hours, 0) ?? 0;
  const totalOvertime = rows?.reduce((s, r) => s + r.overtime_hours, 0) ?? 0;
  const daysRecorded = rows?.reduce((s, r) => s + r.days_recorded, 0) ?? 0;

  const detailEmployee = rows?.find((r) => r.employee_id === selectedEmp);

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Attendance</h1>
          <p className="text-muted-foreground mt-1">
            Track recorded hours and overtime across the team.
          </p>
        </div>
        <div className="w-44">
          <Select value={sel} onValueChange={(v) => { setSel(v); setSelectedEmp(null); }}>
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

      {/* Team summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Team Members"
          value={String(rows?.length ?? 0)}
          sub="With recorded time"
          icon={<Users className="h-5 w-5 text-blue-600" />}
          bgColor="bg-blue-50"
        />
        <StatCard
          title="Total Hours"
          value={`${totalHours}h`}
          sub={monthLabel(year, month)}
          icon={<Clock className="h-5 w-5 text-green-600" />}
          bgColor="bg-green-50"
        />
        <StatCard
          title="Days Recorded"
          value={String(daysRecorded)}
          sub={monthLabel(year, month)}
          icon={<CalendarDays className="h-5 w-5 text-amber-600" />}
          bgColor="bg-amber-50"
        />
        <StatCard
          title="Overtime"
          value={`${totalOvertime}h`}
          sub="Beyond 8h / day"
          icon={<Zap className="h-5 w-5 text-red-600" />}
          bgColor="bg-red-50"
        />
      </div>

      {/* Team table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Team — {monthLabel(year, month)}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !rows || rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No time recorded this month.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Days</TableHead>
                  <TableHead>Total Hours</TableHead>
                  <TableHead>Avg / Day</TableHead>
                  <TableHead>Overtime</TableHead>
                  <TableHead className="w-8" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow
                    key={r.employee_id}
                    onClick={() =>
                      setSelectedEmp(selectedEmp === r.employee_id ? null : r.employee_id)
                    }
                    className="cursor-pointer"
                  >
                    <TableCell className="font-medium">{r.employee_name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {r.department ?? "—"}
                    </TableCell>
                    <TableCell>{r.days_recorded}</TableCell>
                    <TableCell className="font-medium">{r.total_hours}h</TableCell>
                    <TableCell>{r.avg_daily_hours != null ? `${r.avg_daily_hours}h` : "—"}</TableCell>
                    <TableCell>
                      {r.overtime_hours > 0 ? (
                        <Badge variant="destructive">{r.overtime_hours}h</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <ChevronRight
                        className={`h-4 w-4 text-muted-foreground transition-transform ${
                          selectedEmp === r.employee_id ? "rotate-90" : ""
                        }`}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Per-employee detail */}
      {detailEmployee && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {detailEmployee.employee_name} — {monthLabel(year, month)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {detail && detail.items.length > 0 ? (
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
                  {[...detail.items]
                    .sort((a, b) => b.work_date.localeCompare(a.work_date))
                    .map((e) => (
                      <TableRow key={e.id}>
                        <TableCell className="font-medium">{formatWorkDate(e.work_date)}</TableCell>
                        <TableCell>{formatClock(e.clock_in)}</TableCell>
                        <TableCell>{e.clock_out ? formatClock(e.clock_out) : <Badge variant="secondary">Open</Badge>}</TableCell>
                        <TableCell>{e.breaks_minutes > 0 ? `${e.breaks_minutes}m` : "—"}</TableCell>
                        <TableCell className="font-medium">{e.hours != null ? `${e.hours}h` : "—"}</TableCell>
                        <TableCell className="text-muted-foreground">{e.notes || "—"}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">No time recorded this month.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
