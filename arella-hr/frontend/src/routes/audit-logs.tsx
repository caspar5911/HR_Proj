import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAuditLogs, type AuditLogOut } from "@/lib/audit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { ChevronDown, ChevronRight, FileClock } from "lucide-react";

const ENTITIES = [
  "",
  "employee",
  "leave_request",
  "leave_balance",
  "leave_type",
  "payroll_run",
  "payroll_entry",
  "deduction_rule",
  "department",
  "user",
];

const RANGES = [
  { label: "All time", days: 0 },
  { label: "Last 24 hours", days: 1 },
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
];

function actionLabel(action: string): { verb: string; cls: string } {
  const verb = action.includes(".") ? action.split(".").slice(1).join(".") : action;
  if (verb.startsWith("create")) return { verb, cls: "bg-green-100 text-green-800" };
  if (verb.startsWith("delete")) return { verb, cls: "bg-red-100 text-red-800" };
  if (verb.startsWith("reject")) return { verb, cls: "bg-red-100 text-red-800" };
  if (verb.startsWith("approve")) return { verb, cls: "bg-blue-100 text-blue-800" };
  if (verb === "login") return { verb, cls: "bg-violet-100 text-violet-800" };
  if (verb.startsWith("process")) return { verb, cls: "bg-amber-100 text-amber-800" };
  return { verb, cls: "bg-gray-100 text-gray-700" };
}

function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return "∅";
  if (typeof v === "string") return v.length > 40 ? `${v.slice(0, 40)}…` : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    const s = JSON.stringify(v);
    return s.length > 40 ? `${s.slice(0, 40)}…` : s;
  } catch {
    return String(v);
  }
}

function fmtTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const [entity, setEntity] = useState("");
  const [range, setRange] = useState(30);

  const start =
    range > 0
      ? new Date(Date.now() - range * 86400000).toISOString()
      : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", { page, entity, range }],
    queryFn: () => listAuditLogs({ page, page_size: 20, entity: entity || undefined, start }),
  });

  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggle = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const items = data?.items ?? [];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Audit log</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Immutable record of every change across the system.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={entity} onValueChange={(v) => { setEntity(v); setPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All entities" />
          </SelectTrigger>
          <SelectContent>
            {ENTITIES.map((e) => (
              <SelectItem key={e} value={e}>
                {e === "" ? "All entities" : e.replace(/_/g, " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={String(range)} onValueChange={(v) => { setRange(Number(v)); setPage(1); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGES.map((r) => (
              <SelectItem key={r.days} value={String(r.days)}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {data ? `${data.total} events` : ""}
        </span>
      </div>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Loading audit log…</p>
          ) : items.length === 0 ? (
            <div className="py-12 text-center">
              <FileClock className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">No audit events in this range.</p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[140px]" />
                    <TableHead>When</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Changes</TableHead>
                    <TableHead>IP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((log) => {
                    const open = expanded.has(log.id);
                    const { verb, cls } = actionLabel(log.action);
                    const changes = log.changes as
                      | Record<string, { old?: unknown; new?: unknown }>
                      | null;
                    return (
                      <FragmentRow
                        key={log.id}
                        log={log}
                        open={open}
                        onToggle={() => toggle(log.id)}
                        verb={verb}
                        cls={cls}
                        changes={changes}
                      />
                    );
                  })}
                </TableBody>
              </Table>
              {data && data.total_pages > 1 && (
                <div className="mt-4 flex justify-end">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          className={data.page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                        />
                      </PaginationItem>
                      {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                        .filter((p) => p === 1 || p === data.total_pages || Math.abs(p - data.page) <= 1)
                        .reduce((acc: number[], p: number, idx: number, arr: number[]) => {
                          if (idx > 0 && p - arr[idx - 1] > 1) acc.push(-1);
                          acc.push(p);
                          return acc;
                        }, [])
                        .map((p) =>
                          p === -1 ? (
                            <PaginationItem key="el">
                              <PaginationEllipsis />
                            </PaginationItem>
                          ) : (
                            <PaginationItem key={p}>
                              <PaginationLink onClick={() => setPage(p)} isActive={data!.page === p} className="cursor-pointer">
                                {p}
                              </PaginationLink>
                            </PaginationItem>
                          )
                        )}
                      <PaginationItem>
                        <PaginationNext
                          onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                          className={data.page >= data.total_pages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FragmentRow({
  log,
  open,
  onToggle,
  verb,
  cls,
  changes,
}: {
  log: AuditLogOut;
  open: boolean;
  onToggle: () => void;
  verb: string;
  cls: string;
  changes: Record<string, { old?: unknown; new?: unknown }> | null;
}) {
  const hasChanges = changes && Object.keys(changes).length > 0;
  return (
    <>
      <TableRow className="cursor-pointer" onClick={hasChanges ? onToggle : undefined}>
        <TableCell>
          <Button
            variant="ghost"
            size="sm"
            className={hasChanges ? "h-7 w-7 p-0" : "h-7 w-7 p-0 opacity-0"}
            tabIndex={-1}
          >
            {hasChanges ? (
              open ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )
            ) : null}
          </Button>
        </TableCell>
        <TableCell className="text-sm whitespace-nowrap">{fmtTimestamp(log.timestamp)}</TableCell>
        <TableCell className="text-sm">
          {log.user_email ?? <span className="text-muted-foreground">system</span>}
        </TableCell>
        <TableCell>
          <Badge variant="outline" className={cls}>
            {verb}
          </Badge>
        </TableCell>
        <TableCell className="text-sm">
          {log.entity}
          {log.entity_id != null && (
            <span className="text-muted-foreground"> #{log.entity_id}</span>
          )}
        </TableCell>
        <TableCell className="text-xs text-muted-foreground">
          {hasChanges ? `${Object.keys(changes!).length} field${Object.keys(changes!).length === 1 ? "" : "s"}` : "—"}
        </TableCell>
        <TableCell className="text-xs text-muted-foreground">
          {log.ip_address ?? "—"}
        </TableCell>
      </TableRow>
      {open && hasChanges && (
        <TableRow>
          <TableCell colSpan={7} className="bg-muted/40">
            <div className="space-y-2 py-1">
              {Object.entries(changes!).map(([field, v]) => (
                <div key={field} className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono font-medium w-40 shrink-0">{field}</span>
                  <span className="text-red-600 line-through">{fmtVal(v?.old)}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-green-700 font-medium">{fmtVal(v?.new)}</span>
                </div>
              ))}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
