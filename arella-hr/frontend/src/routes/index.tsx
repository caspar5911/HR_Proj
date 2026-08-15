import { RouteObject } from "react-router-dom";
import { AuthenticatedRoute, PublicOnlyRoute, RoleRestrictedRoute } from "./guards";
import { MainLayout } from "./layout";
import DashboardPage from "./dashboard";
import LoginPage from "./login";
import EmployeesPage from "./employees";
import EmployeeProfilePage from "./employee";
import LeavePage from "./leave";
import OrgChartPage from "./org-chart";
import MyHomePage from "./my-home";
import AuditLogsPage from "./audit-logs";
import { PayrollPage } from "./payroll";
import MyTimePage from "./my-time";
import AttendancePage from "./attendance";

/**
 * Route configuration for the application.
 *
 * Authenticated routes are wrapped in MainLayout (sidebar) + AuthenticatedRoute
 * guard. Within the layout, role-restricted subtrees mirror the backend's
 * require_role() gates:
 *   - admin+manager: dashboard, employees, org chart, payroll, attendance
 *   - admin only:    audit log
 *   - everyone:      leave, my home, my time
 * Login is behind PublicOnlyRoute (redirects to the role's landing page when
 * already logged in).
 */
export const routes: RouteObject[] = [
  {
    element: <AuthenticatedRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          {
            element: <RoleRestrictedRoute roles={["admin", "manager"]} />,
            children: [
              { index: true, element: <DashboardPage /> },
              { path: "employees", element: <EmployeesPage /> },
              { path: "employees/:employeeId", element: <EmployeeProfilePage /> },
              { path: "org-chart", element: <OrgChartPage /> },
              { path: "payroll", element: <PayrollPage /> },
              { path: "attendance", element: <AttendancePage /> },
            ],
          },
          {
            element: <RoleRestrictedRoute roles={["admin"]} />,
            children: [{ path: "audit-logs", element: <AuditLogsPage /> }],
          },
          { path: "leave", element: <LeavePage /> },
          { path: "my-home", element: <MyHomePage /> },
          { path: "my-time", element: <MyTimePage /> },
        ],
      },
    ],
  },
  {
    element: <PublicOnlyRoute />,
    children: [{ path: "login", element: <LoginPage /> }],
  },
];
