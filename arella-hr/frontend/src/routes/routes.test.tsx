import { describe, it, expect } from "vitest";
import * as React from "react";
import { routes } from "./index";

describe("route configuration", () => {
  it("defines exactly two top-level route trees", () => {
    expect(routes).toHaveLength(2);
  });

  it("wraps app routes behind AuthenticatedRoute -> MainLayout", () => {
    const app = routes[0];
    expect(React.isValidElement(app.element)).toBe(true);

    const layout = app.children?.[0];
    expect(layout).toBeDefined();
    expect(React.isValidElement(layout!.element)).toBe(true);
  });

  it("splits layout routes into role-restricted and open groups", () => {
    const layout = routes[0].children?.[0];
    const pages = layout!.children ?? [];

    // [0] admin+manager subtree, [1] admin-only subtree, [2] leave, [3] my-home
    const staffSubtree = pages[0];
    const adminSubtree = pages[1];
    const openRoutes = pages.slice(2);

    expect(React.isValidElement(staffSubtree.element)).toBe(true);
    expect(React.isValidElement(adminSubtree.element)).toBe(true);

    const staffPaths = (staffSubtree.children ?? [])
      .map((p) => (p.index ? "/" : p.path));
    expect(staffPaths).toEqual([
      "/",
      "employees",
      "employees/:employeeId",
      "org-chart",
      "payroll",
    ]);

    const adminPaths = (adminSubtree.children ?? []).map((p) => p.path);
    expect(adminPaths).toEqual(["audit-logs"]);

    const openPaths = openRoutes.map((p) => p.path);
    expect(openPaths).toEqual(["leave", "my-home"]);

    for (const p of pages) {
      expect(React.isValidElement(p.element)).toBe(true);
    }
  });

  it("keeps login behind PublicOnlyRoute as the only public child", () => {
    const pub = routes[1];
    expect(React.isValidElement(pub.element)).toBe(true);

    const children = pub.children ?? [];
    expect(children).toHaveLength(1);
    expect(children[0].path).toBe("login");
    expect(React.isValidElement(children[0].element)).toBe(true);
  });
});
