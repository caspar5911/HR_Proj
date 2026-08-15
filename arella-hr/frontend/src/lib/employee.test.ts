import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listEmployees,
  getEmployee,
  createEmployee,
  updateEmployee,
  deactivateEmployee,
  restoreEmployee,
  deleteEmployee,
  getOrgTree,
} from "./employee";

const shared = vi.hoisted(() => ({
  calls: [] as Array<{ method: string; url: string; arg1?: unknown }>,
  body: { ok: true, marker: 42 },
}));

vi.mock("./api", () => {
  const mk = (method: string) => (url: string, arg1?: unknown) => {
    shared.calls.push({ method, url, arg1 });
    return Promise.resolve({ data: shared.body, status: 200 });
  };
  return {
    default: {
      get: mk("get"),
      post: mk("post"),
      put: mk("put"),
      patch: mk("patch"),
      delete: mk("delete"),
    },
  };
});

beforeEach(() => {
  shared.calls.length = 0;
});

const last = () => shared.calls[shared.calls.length - 1];

function assertCall(method: string, url: string, arg1?: unknown) {
  const c = last();
  expect(c.method).toBe(method);
  expect(c.url).toBe(url);
  if (arg1 === undefined) expect(c.arg1).toBeUndefined();
  else expect(c.arg1).toEqual(arg1);
}

describe("employee API client", () => {
  it("listEmployees sends GET /employees with all query params", async () => {
    const res = await listEmployees({
      page: 2,
      page_size: 10,
      search: "jo",
      department: "eng",
      status: "active",
    });
    assertCall("get", "/employees", {
      params: { page: 2, page_size: 10, search: "jo", department: "eng", status: "active" },
    });
    // returns the raw axios response (data unwrapped by the caller)
    expect(res.data).toEqual(shared.body);
  });

  it("listEmployees passes an empty params object when called with no args", async () => {
    await listEmployees();
    assertCall("get", "/employees", { params: {} });
  });

  it("getEmployee sends GET /employees/:id", async () => {
    const res = await getEmployee(7);
    assertCall("get", "/employees/7");
    expect(res.data).toEqual(shared.body);
  });

  it("createEmployee sends POST /employees with the payload", async () => {
    const payload = { first_name: "Ada", last_name: "Lovelace", email: "ada@example.com" };
    const res = await createEmployee(payload);
    assertCall("post", "/employees", payload);
    expect(res.data).toEqual(shared.body);
  });

  it("updateEmployee sends PUT /employees/:id with the payload", async () => {
    await updateEmployee(7, { status: "inactive" });
    assertCall("put", "/employees/7", { status: "inactive" });
  });

  it("deactivateEmployee sends PATCH /employees/:id/deactivate", async () => {
    await deactivateEmployee(7);
    assertCall("patch", "/employees/7/deactivate");
  });

  it("restoreEmployee sends PATCH /employees/:id/restore", async () => {
    await restoreEmployee(7);
    assertCall("patch", "/employees/7/restore");
  });

  it("deleteEmployee sends DELETE /employees/:id", async () => {
    await deleteEmployee(7);
    assertCall("delete", "/employees/7");
  });

  it("getOrgTree sends GET /employees/org-tree", async () => {
    const res = await getOrgTree();
    assertCall("get", "/employees/org-tree");
    expect(res.data).toEqual(shared.body);
  });
});
