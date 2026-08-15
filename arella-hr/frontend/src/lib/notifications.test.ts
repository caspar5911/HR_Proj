import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
} from "./notifications";

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

describe("notifications API client", () => {
  it("listNotifications sends GET /notifications/ with default pagination", async () => {
    const res = await listNotifications();
    assertCall("get", "/notifications/", { params: { page: 1, page_size: 20 } });
    expect(res).toEqual(shared.body);
  });

  it("listNotifications honors explicit page/size", async () => {
    await listNotifications(3, 50);
    assertCall("get", "/notifications/", { params: { page: 3, page_size: 50 } });
  });

  it("getUnreadCount sends GET /notifications/unread-count", async () => {
    const res = await getUnreadCount();
    assertCall("get", "/notifications/unread-count");
    expect(res).toEqual(shared.body);
  });

  it("markNotificationRead sends PATCH /notifications/:id/read", async () => {
    const res = await markNotificationRead(7);
    assertCall("patch", "/notifications/7/read");
    expect(res).toEqual(shared.body);
  });

  it("markAllNotificationsRead sends POST /notifications/read-all", async () => {
    const res = await markAllNotificationsRead();
    assertCall("post", "/notifications/read-all");
    expect(res).toEqual(shared.body);
  });
});
