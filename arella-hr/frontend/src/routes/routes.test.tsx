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

    const pages = layout!.children ?? [];
    const paths = pages.map((p) => (p.index ? "/" : p.path));
    expect(paths).toEqual(["/", "employees", "leave", "payroll"]);
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
