import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getOrgTree, type OrgNode } from "@/lib/employee";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  ChevronDown,
  ChevronRight,
  Network,
  Users,
  Building2,
} from "lucide-react";

/** Deterministic accent color per employee id. */
const AVATAR_COLORS = [
  "from-blue-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-rose-500 to-pink-600",
  "from-amber-500 to-orange-600",
  "from-violet-500 to-purple-600",
  "from-cyan-500 to-sky-600",
];

function avatarGradient(id: number): string {
  return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

function initialsOf(n: OrgNode): string {
  return `${n.first_name.charAt(0)}${n.last_name.charAt(0)}`;
}

export default function OrgChartPage() {
  const { data: roots, isLoading, error } = useQuery({
    queryKey: ["org-tree"],
    queryFn: () => getOrgTree().then((r) => r.data),
  });

  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [dept, setDept] = useState<string>("");

  const departments = useMemo(() => {
    const names = new Set<string>();
    const walk = (nodes: OrgNode[]) => {
      nodes.forEach((n) => {
        if (n.department) names.add(n.department);
        walk(n.reports);
      });
    };
    walk(roots ?? []);
    return [...names].sort();
  }, [roots]);

  const visibleCount = useMemo(() => {
    let count = 0;
    const walk = (nodes: OrgNode[]) => {
      nodes.forEach((n) => {
        if (!dept || n.department === dept) count++;
        walk(n.reports);
      });
    };
    walk(roots ?? []);
    return count;
  }, [roots, dept]);

  const toggle = (id: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (error) {
    return (
      <div className="p-8">
        <p className="text-sm text-destructive">Could not load the org chart.</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Org chart</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Reporting lines across the company. Click a name to open the profile.
        </p>
      </div>

      {/* Summary + department filter */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-lg bg-white border border-border px-3 py-1.5 text-sm">
          <Users className="h-4 w-4 text-muted-foreground" />
          <strong>{visibleCount}</strong> people
        </span>
        <span className="inline-flex items-center gap-2 rounded-lg bg-white border border-border px-3 py-1.5 text-sm">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <strong>{departments.length}</strong> departments
        </span>
        <div className="flex flex-wrap gap-1.5 ml-auto">
          <button
            onClick={() => setDept("")}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              dept === ""
                ? "bg-blue-600 border-blue-600 text-white"
                : "bg-white border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            All
          </button>
          {departments.map((d) => (
            <button
              key={d}
              onClick={() => setDept(d === dept ? "" : d)}
              className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                dept === d
                  ? "bg-blue-600 border-blue-600 text-white"
                  : "bg-white border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">Loading org chart…</p>
      ) : (
        <Card>
          <CardContent className="pt-6">
            {(roots ?? []).length === 0 ? (
              <div className="py-12 text-center">
                <Network className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">No employees yet.</p>
              </div>
            ) : (
              <div className="space-y-1">
                {(roots ?? []).map((n) => (
                  <OrgTreeNode
                    key={n.id}
                    node={n}
                    depth={0}
                    dept={dept}
                    collapsed={collapsed}
                    onToggle={toggle}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function OrgTreeNode({
  node,
  depth,
  dept,
  collapsed,
  onToggle,
}: {
  node: OrgNode;
  depth: number;
  dept: string;
  collapsed: Set<number>;
  onToggle: (id: number) => void;
}) {
  // A node hidden by the department filter is hidden with its whole subtree.
  if (dept && node.department !== dept) return null;

  const hasReports = node.reports.length > 0;
  const isCollapsed = collapsed.has(node.id);
  const active = node.status === "active";

  return (
    <div>
      <div
        className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/60"
        style={{ marginLeft: depth * 28 }}
      >
        {/* Expand/collapse or spacer */}
        {hasReports ? (
          <button
            onClick={() => onToggle(node.id)}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
            aria-label={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        ) : (
          <span className="flex h-6 w-6 shrink-0 items-center justify-center">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
          </span>
        )}

        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-sm font-bold text-white ${avatarGradient(
            node.id
          )}`}
        >
          {initialsOf(node)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/employees/${node.id}`}
              className="truncate text-sm font-semibold hover:text-blue-600 transition-colors"
            >
              {node.first_name} {node.last_name}
            </Link>
            {!active && <Badge variant="secondary">{node.status.replace("_", " ")}</Badge>}
            {depth === 0 && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                Top level
              </span>
            )}
          </div>
          <p className="truncate text-xs text-muted-foreground mt-0.5">
            {[node.position, node.department].filter(Boolean).join(" · ")}
          </p>
        </div>

        {hasReports && !isCollapsed && (
          <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground tabular-nums">
            {node.reports.length}
          </span>
        )}
      </div>

      {!isCollapsed &&
        node.reports.map((child) => (
          <div key={child.id} className="relative" style={{ marginLeft: depth * 28 + 14 }}>
            {/* vertical guide line */}
            <span className="absolute left-0 top-0 bottom-0 w-px bg-border" aria-hidden />
            <OrgTreeNode
              node={child}
              depth={depth + 1}
              dept={dept}
              collapsed={collapsed}
              onToggle={onToggle}
            />
          </div>
        ))}
    </div>
  );
}
