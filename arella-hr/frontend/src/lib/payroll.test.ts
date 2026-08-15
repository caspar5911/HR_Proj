import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listPayrollRuns,
  getPayrollRun,
  createPayrollRun,
  updatePayrollRun,
  processPayrollRun,
  calculatePayrollRun,
  deletePayrollRun,
  listPayrollEntries,
  listDeductionRules,
  getDeductionRule,
  createDeductionRule,
  updateDeductionRule,
  deleteDeductionRule,
  type DeductionRuleCreate,
} from "./payroll";

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

describe("payroll API client", () => {
  it("listPayrollRuns builds the query string in canonical order and unwraps .data", async () => {
    const res = await listPayrollRuns({ page: 2, page_size: 5, status: "draft", search: "june" });
    assertCall("get", "/payroll-runs?page=2&page_size=5&status=draft&search=june");
    expect(res).toEqual(shared.body);
  });

  it("listPayrollRuns with no params sends an empty query string", async () => {
    await listPayrollRuns();
    assertCall("get", "/payroll-runs?");
  });

  it("getPayrollRun sends GET /payroll-runs/:id", async () => {
    const res = await getPayrollRun(3);
    assertCall("get", "/payroll-runs/3");
    expect(res).toEqual(shared.body);
  });

  it("createPayrollRun sends POST /payroll-runs with the payload", async () => {
    const payload = { period_start: "2026-06-01", period_end: "2026-06-30", notes: "June" };
    await createPayrollRun(payload);
    assertCall("post", "/payroll-runs", payload);
  });

  it("updatePayrollRun sends PUT /payroll-runs/:id", async () => {
    await updatePayrollRun(3, { status: "paid" });
    assertCall("put", "/payroll-runs/3", { status: "paid" });
  });

  it("processPayrollRun sends POST /payroll-runs/:id/process without a body", async () => {
    await processPayrollRun(3);
    assertCall("post", "/payroll-runs/3/process");
  });

  it("calculatePayrollRun sends POST /payroll-runs/:id/calculate", async () => {
    await calculatePayrollRun(3);
    assertCall("post", "/payroll-runs/3/calculate");
  });

  it("deletePayrollRun sends DELETE /payroll-runs/:id", async () => {
    const res = await deletePayrollRun(3);
    assertCall("delete", "/payroll-runs/3");
    expect(res).toBeUndefined();
  });

  it("listPayrollEntries builds /payroll-runs/:id/entries with pagination", async () => {
    const res = await listPayrollEntries(9, { page: 2, page_size: 50 });
    assertCall("get", "/payroll-runs/9/entries?page=2&page_size=50");
    expect(res).toEqual(shared.body);
  });

  it("listPayrollEntries with no params sends an empty query string", async () => {
    await listPayrollEntries(9);
    assertCall("get", "/payroll-runs/9/entries?");
  });

  it("listDeductionRules serializes active_only and search", async () => {
    await listDeductionRules({ active_only: true, search: "tax" });
    assertCall("get", "/deduction-rules?active_only=true&search=tax");
  });

  it("listDeductionRules with no params sends an empty query string", async () => {
    await listDeductionRules();
    assertCall("get", "/deduction-rules?");
  });

  it("getDeductionRule sends GET /deduction-rules/:id", async () => {
    const res = await getDeductionRule(4);
    assertCall("get", "/deduction-rules/4");
    expect(res).toEqual(shared.body);
  });

  it("createDeductionRule sends POST /deduction-rules", async () => {
    const payload: DeductionRuleCreate = { name: "Tax", value: 10, deduction_type: "percentage" };
    await createDeductionRule(payload);
    assertCall("post", "/deduction-rules", payload);
  });

  it("updateDeductionRule sends PUT /deduction-rules/:id", async () => {
    await updateDeductionRule(4, { active: false });
    assertCall("put", "/deduction-rules/4", { active: false });
  });

  it("deleteDeductionRule sends DELETE /deduction-rules/:id", async () => {
    const res = await deleteDeductionRule(4);
    assertCall("delete", "/deduction-rules/4");
    expect(res).toBeUndefined();
  });
});
