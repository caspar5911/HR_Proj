import { NavLink, Outlet } from "react-router-dom";
import {
  Award,
  CalendarCheck,
  CalendarDays,
  Clock,
  FileClock,
  Home,
  LayoutDashboard,
  LogOut,
  Network,
  ShieldCheck,
  Users,
  Wallet,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { NotificationBell } from "@/components/NotificationBell";

/**
 * Navigation is role-aware: managers/admins get the full operations menu,
 * plain employees get a slim self-service menu (My Home + their leave).
 */
const STAFF_NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/employees", label: "Employees", icon: Users },
  { to: "/org-chart", label: "Org Chart", icon: Network },
  { to: "/leave", label: "Leave", icon: CalendarDays },
  { to: "/payroll", label: "Payroll", icon: Wallet },
  { to: "/attendance", label: "Attendance", icon: CalendarCheck },
  { to: "/performance", label: "Performance", icon: Award },
  { to: "/my-home", label: "My Home", icon: Home },
  { to: "/my-time", label: "My Time", icon: Clock },
  { to: "/audit-logs", label: "Audit Log", icon: FileClock },
];

const EMPLOYEE_NAV = [
  { to: "/my-home", label: "My Home", icon: Home, end: true },
  { to: "/leave", label: "My Leave", icon: CalendarDays },
  { to: "/my-time", label: "My Time", icon: Clock },
  { to: "/my-reviews", label: "My Reviews", icon: Award },
];

export function MainLayout() {
  const { user, logout } = useAuth();
  // Audit Log is admin-only on the backend — hide it for managers.
  const baseNav = user?.role === "employee" ? EMPLOYEE_NAV : STAFF_NAV;
  const nav = user?.role === "admin" ? baseNav : baseNav.filter((n) => n.to !== "/audit-logs");

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 bg-slate-900 text-white flex flex-col">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-bold text-lg">
              A
            </div>
            <div>
              <h1 className="text-base font-bold leading-tight">Arella HR</h1>
              <p className="text-[11px] text-slate-400">People &amp; payroll platform</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-800">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-700 text-sm font-semibold text-slate-200">
              {(user?.email ?? "?")
                .split("@")[0]
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-100">{user?.email}</p>
              <RoleBadge role={user?.role} />
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-x-auto">
        <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-end border-b border-gray-200 bg-white/95 px-6 backdrop-blur">
          <NotificationBell />
        </header>
        <div className="flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function RoleBadge({ role }: { role?: string }) {
  const styles: Record<string, string> = {
    admin: "bg-violet-500/20 text-violet-300 ring-violet-500/30",
    manager: "bg-amber-500/20 text-amber-300 ring-amber-500/30",
    employee: "bg-sky-500/20 text-sky-300 ring-sky-500/30",
  };
  const label = role ? role.charAt(0).toUpperCase() + role.slice(1) : "Unknown";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ${
        styles[role ?? ""] ?? "bg-slate-500/20 text-slate-300 ring-slate-500/30"
      }`}
    >
      {role === "admin" && <ShieldCheck className="h-3 w-3" />}
      {label}
    </span>
  );
}
