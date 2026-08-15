import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

/** Redirect unauthenticated users to /login. */
export function AuthenticatedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

/** Redirect logged-in users away from /login. */
export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return isAuthenticated ? <Navigate to="/" replace /> : <Outlet />;
}