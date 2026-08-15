import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  BellRing,
  CalendarDays,
  CheckCheck,
  CheckCircle2,
  Inbox,
  Wallet,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import {
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from "@/lib/notifications";
import { cn } from "@/lib/utils";

/** Poll cadence for the unread badge. */
const REFRESH_MS = 30_000;

const TYPE_ICONS: Record<string, { icon: LucideIcon; className: string }> = {
  leave_requested: { icon: CalendarDays, className: "bg-amber-100 text-amber-700" },
  leave_approved: { icon: CheckCircle2, className: "bg-emerald-100 text-emerald-700" },
  leave_rejected: { icon: XCircle, className: "bg-rose-100 text-rose-700" },
  payroll_processed: { icon: Wallet, className: "bg-indigo-100 text-indigo-700" },
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const mins = Math.floor((Date.now() - then) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * Top-bar notification bell: unread badge (polled every 30s) plus a
 * dropdown panel with the newest notifications. Clicking an item marks it
 * read (optimistically) and follows its link.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const rootRef = useRef<HTMLDivElement>(null);

  const { data: unreadData } = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: getUnreadCount,
    refetchInterval: REFRESH_MS,
  });
  const unread = unreadData?.unread ?? 0;

  const { data: listData, isPending } = useQuery({
    queryKey: ["notifications", "list", 1],
    queryFn: () => listNotifications(1, 15),
    enabled: open,
    staleTime: 30_000,
  });

  const mReadAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      qc.setQueryData(["notifications", "unread"], { unread: 0 });
      qc.invalidateQueries({ queryKey: ["notifications", "list"] });
    },
  });

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function handleOpenItem(n: Notification) {
    setOpen(false);
    if (!n.read) {
      // Optimistic: mark read locally, refetch if the PATCH fails.
      qc.setQueryData(["notifications", "list", 1], (old: any) =>
        old ? { ...old, items: old.items.map((i: Notification) => (i.id === n.id ? { ...i, read: true } : i)) } : old
      );
      qc.setQueryData(["notifications", "unread"], (old: any) =>
        old ? { ...old, unread: Math.max(0, old.unread - 1) } : old
      );
      markNotificationRead(n.id).catch(() => qc.invalidateQueries({ queryKey: ["notifications"] }));
    }
    if (n.link) navigate(n.link);
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        title="Notifications"
        className={cn(
          "relative rounded-lg p-2 transition-colors",
          open ? "bg-blue-50 text-blue-600" : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        )}
      >
        {unread > 0 ? <BellRing className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-96 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <p className="text-sm font-semibold text-gray-900">
              Notifications
              {unread > 0 && <span className="ml-1.5 text-xs font-normal text-gray-400">{unread} new</span>}
            </p>
            <button
              type="button"
              onClick={() => mReadAll.mutate()}
              disabled={unread === 0}
              title="Mark all as read"
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-gray-300"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {isPending ? (
              <p className="px-4 py-6 text-center text-sm text-gray-400">Loading…</p>
            ) : listData && listData.items.length > 0 ? (
              <ul className="divide-y divide-gray-100">
                {listData.items.map((n) => {
                  const { icon: Icon, className } = TYPE_ICONS[n.type] ?? {
                    icon: Bell,
                    className: "bg-gray-100 text-gray-600",
                  };
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => handleOpenItem(n)}
                        className={cn(
                          "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50",
                          !n.read && "bg-blue-50/60 hover:bg-blue-50"
                        )}
                      >
                        <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full", className)}>
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center justify-between gap-2">
                            <span className={cn("truncate text-sm", !n.read ? "font-semibold text-gray-900" : "font-medium text-gray-700")}>
                              {n.title}
                            </span>
                            <span className="shrink-0 text-[11px] text-gray-400">{timeAgo(n.created_at)}</span>
                          </span>
                          <span className="mt-0.5 line-clamp-2 block text-xs text-gray-500">{n.body}</span>
                        </span>
                        {!n.read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-blue-500" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="flex flex-col items-center gap-2 px-4 py-10 text-gray-400">
                <Inbox className="h-6 w-6" />
                <p className="text-sm">You're all caught up</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
