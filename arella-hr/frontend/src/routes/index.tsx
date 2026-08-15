import { RouteObject } from "react-router-dom";
import { AuthenticatedRoute, PublicOnlyRoute } from "./guards";
import { MainLayout } from "./layout";
import DashboardPage from "./dashboard";
import LoginPage from "./login";
import EmployeesPage from "./employees";
import LeavePage from "./leave";
import { PayrollPage } from "./payroll";

/**
 * Route configuration for the application.
 * Authenticated routes are wrapped in MainLayout (sidebar) + AuthenticatedRoute guard.
 * Login is behind PublicOnlyRoute (redirects to / if already logged in).
 */
export const routes: RouteObject[] = [
  {
    element: <AuthenticatedRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "employees", element: <EmployeesPage /> },
          { path: "leave", element: <LeavePage /> },
          { path: "payroll", element: <PayrollPage /> },
        ],
      },
    ],
  },
  {
    element: <PublicOnlyRoute />,
    children: [{ path: "login", element: <LoginPage /> }],
  },
];
