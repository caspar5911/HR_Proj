import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * Tests the axios instance and its interceptors in lib/api.ts.
 * `axios` is mocked so no network access happens; we capture the interceptors
 * the module registers and drive them directly.
 */

const captured = vi.hoisted(() => ({
  requestHandlers: [] as Array<(config: any) => any>,
  onSuccess: [] as Array<(r: any) => any>,
  onError: [] as Array<(e: any) => any>,
  createConfig: null as any,
}));

vi.mock("axios", () => {
  const interceptors = {
    request: {
      use: (onFulfilled: any) => {
        captured.requestHandlers.push(onFulfilled);
      },
    },
    response: {
      use: (onFulfilled: any, onRejected?: any) => {
        captured.onSuccess.push(onFulfilled);
        if (onRejected) captured.onError.push(onRejected);
      },
    },
  };
  return {
    default: {
      create: (config: any) => {
        captured.createConfig = config;
        return { interceptors };
      },
    },
  };
});

import api from "./api";

function makeLocalStorage() {
  const store = new Map<string, string>();
  return {
    getItem: (k: string) => (store.has(k) ? (store.get(k) as string) : null),
    setItem: (k: string, v: string) => {
      store.set(k, String(v));
    },
    removeItem: (k: string) => {
      store.delete(k);
    },
    clear: () => store.clear(),
  };
}

function attachWindow(win: { location: { href: string } }) {
  vi.stubGlobal("window", win);
  return win;
}

describe("lib/api axios instance", () => {
  let ls: ReturnType<typeof makeLocalStorage>;
  let win: { location: { href: string } };

  beforeEach(() => {
    // NOTE: the interceptor handlers are registered once at module-import time
    // and must NOT be cleared here — tests drive them directly.
    ls = makeLocalStorage();
    vi.stubGlobal("localStorage", ls);
    win = attachWindow({ location: { href: "" } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("is created against the /api/v1 base URL with JSON content type", () => {
    expect(captured.createConfig.baseURL).toBe("/api/v1");
    expect(captured.createConfig.headers["Content-Type"]).toBe("application/json");
  });

  describe("request interceptor", () => {
    it("attaches Authorization header when a token is present", () => {
      ls.setItem("access_token", "tok-123");
      const config: any = { headers: {} };
      const out = captured.requestHandlers[0](config);
      expect(out.headers.Authorization).toBe("Bearer tok-123");
    });

    it("does not set Authorization when no token is stored", () => {
      const config: any = { headers: {} };
      const out = captured.requestHandlers[0](config);
      expect(out.headers.Authorization).toBeUndefined();
    });
  });

  describe("response interceptors", () => {
    it("passes successful responses through unchanged", () => {
      const payload = { data: { ok: true } };
      expect(captured.onSuccess[0](payload)).toBe(payload);
    });

    it("clears tokens and redirects to /login on 401", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "stale-r");
      const error = { response: { status: 401 } };
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(ls.getItem("access_token")).toBeNull();
      expect(ls.getItem("refresh_token")).toBeNull();
      // Hash routing: login lives in the fragment, after whatever base path
      // the app was built with ("/" locally, "/<repo>/" when CI sets
      // VITE_BASE_PATH, as for GitHub Pages).
      expect(win.location.href).toMatch(/#\/login$/);
    });

    it("does not redirect or clear tokens on non-401 errors", async () => {
      ls.setItem("access_token", "keep");
      const error = { response: { status: 500 } };
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(ls.getItem("access_token")).toBe("keep");
      expect(win.location.href).toBe("");
    });

    it("rejects errors without a response object as-is", async () => {
      const error = new Error("network down");
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(win.location.href).toBe("");
    });
  });

  it("exposes the mock instance as the default export (interceptor wiring ran)", () => {
    expect((api as any).interceptors).toBeDefined();
  });
});
