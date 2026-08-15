import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

type Role = "admin" | "manager" | "employee";

/** Where each role lands after login (or when a route is denied). */
function landingForRole(role: string | undefined): string {
  return role === "employee" ? "/my-home" : "/";
}

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center">Loading...</div>
  );
}

/** Redirect unauthenticated users to /login. */
export function AuthenticatedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <Loading />;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

/**
 * Redirect logged-in users away from /login, to the landing page that fits
 * their role (employees start in self-service "My Home").
 */
export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) return <Loading />;
  return isAuthenticated ? (
    <Navigate to={landingForRole(user?.role)} replace />
  ) : (
    <Outlet />
  );
}

/**
 * Restrict a route subtree to the given roles; everyone else is bounced to
 * their landing page. Mirrors the backend's require_role() gates so the UI
 * never renders a page whose data the API would 403 anyway.
 */
export function RoleRestrictedRoute({ roles }: { roles: Role[] }) {
  const { user, isLoading } = useAuth();

  if (isLoading) return <Loading />;
  if (user && !roles.includes(user.role as Role)) {
    return <Navigate to={landingForRole(user.role)} replace />;
  }
  return <Outlet />;
}
