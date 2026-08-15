import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listDepartments,
  getDepartment,
  createDepartment,
  updateDepartment,
  listLeaveTypes,
  getLeaveType,
  createLeaveType,
  updateLeaveType,
  listLeaveBalances,
  createLeaveBalance,
  listLeaveRequests,
  getLeaveRequest,
  createLeaveRequest,
  approveLeaveRequest,
  rejectLeaveRequest,
  cancelLeaveRequest,
} from "./leave";

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

describe("leave API client", () => {
  it("listDepartments sends GET /departments/ with default skip/limit", async () => {
    const res = await listDepartments();
    assertCall("get", "/departments/", { params: { skip: 0, limit: 100 } });
    expect(res).toEqual(shared.body);
  });

  it("listDepartments honors explicit skip/limit", async () => {
    await listDepartments(10, 50);
    assertCall("get", "/departments/", { params: { skip: 10, limit: 50 } });
  });

  it("getDepartment sends GET /departments/:id", async () => {
    const res = await getDepartment(5);
    assertCall("get", "/departments/5");
    expect(res).toEqual(shared.body);
  });

  it("createDepartment sends POST /departments/ with the payload", async () => {
    const payload = { name: "Engineering", description: "builds things" };
    await createDepartment(payload);
    assertCall("post", "/departments/", payload);
  });

  it("updateDepartment sends PUT /departments/:id", async () => {
    await updateDepartment(5, { name: "Engineering 2.0" });
    assertCall("put", "/departments/5", { name: "Engineering 2.0" });
  });

  it("listLeaveTypes sends active_only=true by default", async () => {
    await listLeaveTypes();
    assertCall("get", "/leave-types/", { params: { active_only: true } });
  });

  it("listLeaveTypes passes through an explicit activeOnly=false", async () => {
    await listLeaveTypes(false);
    assertCall("get", "/leave-types/", { params: { active_only: false } });
  });

  it("getLeaveType sends GET /leave-types/:id", async () => {
    const res = await getLeaveType(2);
    assertCall("get", "/leave-types/2");
    expect(res).toEqual(shared.body);
  });

  it("createLeaveType sends POST /leave-types/ with the payload", async () => {
    const payload = { name: "Sick", days_per_year: 10, is_paid: true };
    await createLeaveType(payload);
    assertCall("post", "/leave-types/", payload);
  });

  it("updateLeaveType sends PUT /leave-types/:id", async () => {
    await updateLeaveType(2, { active: false });
    assertCall("put", "/leave-types/2", { active: false });
  });

  it("listLeaveBalances serializes employee_id and year", async () => {
    const res = await listLeaveBalances(7, 2026);
    assertCall("get", "/leave-balances/", { params: { employee_id: 7, year: 2026 } });
    expect(res).toEqual(shared.body);
  });

  it("listLeaveBalances with no args sends undefined params", async () => {
    await listLeaveBalances();
    assertCall("get", "/leave-balances/", {
      params: { employee_id: undefined, year: undefined },
    });
  });

  it("createLeaveBalance sends POST /leave-balances/ with the payload", async () => {
    const payload = { employee_id: 1, leave_type_id: 2, year: 2026, allocated: 20 };
    await createLeaveBalance(payload);
    assertCall("post", "/leave-balances/", payload);
  });

  it("listLeaveRequests sends default pagination", async () => {
    await listLeaveRequests();
    assertCall("get", "/leave-requests/", {
      params: { page: 1, page_size: 20, status: undefined, leave_type_id: undefined },
    });
  });

  it("listLeaveRequests honors page, size, status and leave_type_id", async () => {
    const res = await listLeaveRequests(2, 10, "pending", 3);
    assertCall("get", "/leave-requests/", {
      params: { page: 2, page_size: 10, status: "pending", leave_type_id: 3 },
    });
    expect(res).toEqual(shared.body);
  });

  it("getLeaveRequest sends GET /leave-requests/:id", async () => {
    const res = await getLeaveRequest(8);
    assertCall("get", "/leave-requests/8");
    expect(res).toEqual(shared.body);
  });

  it("createLeaveRequest sends POST /leave-requests/ with the payload", async () => {
    const payload = { leave_type_id: 1, start_date: "2026-07-01", end_date: "2026-07-05" };
    await createLeaveRequest(payload);
    assertCall("post", "/leave-requests/", payload);
  });

  it("approveLeaveRequest sends PUT /leave-requests/:id/approve with status approved", async () => {
    await approveLeaveRequest(8, { manager_note: "approved" });
    assertCall("put", "/leave-requests/8/approve", {
      status: "approved",
      manager_note: "approved",
    });
  });

  it("rejectLeaveRequest sends PUT /leave-requests/:id/reject with status rejected", async () => {
    await rejectLeaveRequest(8, { manager_note: "not this time" });
    assertCall("put", "/leave-requests/8/reject", {
      status: "rejected",
      manager_note: "not this time",
    });
  });

  it("cancelLeaveRequest sends DELETE /leave-requests/:id", async () => {
    const res = await cancelLeaveRequest(8);
    assertCall("delete", "/leave-requests/8");
    expect(res).toEqual(shared.body);
  });
});
