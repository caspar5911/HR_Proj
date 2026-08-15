import { Link, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function MainLayout() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-xl font-bold">Arella HR</h1>
          <p className="text-xs text-slate-400 mt-1">HR Management System</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <Link to="/" className="block px-3 py-2 rounded-md hover:bg-slate-700 transition-colors">
            Dashboard
          </Link>
          <Link to="/employees" className="block px-3 py-2 rounded-md hover:bg-slate-700 transition-colors">
            Employees
          </Link>
          <Link to="/leave" className="block px-3 py-2 rounded-md hover:bg-slate-700 transition-colors">
            Leave
          </Link>
          <Link to="/payroll" className="block px-3 py-2 rounded-md hover:bg-slate-700 transition-colors">
            Payroll
          </Link>
        </nav>
        <UserMenu />
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50">
        <Outlet />
      </main>
    </div>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();

  return (
    <div className="p-4 border-t border-slate-700">
      <div className="text-sm mb-2">
        {user?.email}
        <br />
        <span className="text-slate-400 capitalize">{user?.role}</span>
      </div>
      <button
        onClick={logout}
        className="w-full px-3 py-2 text-sm rounded-md bg-slate-700 hover:bg-slate-600 transition-colors"
      >
        Logout
      </button>
    </div>
  );
}