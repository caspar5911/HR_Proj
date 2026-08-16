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
  retryCalls: [] as Array<any>,
  postCalls: [] as Array<{ url: string; data: any }>,
  postImpl: null as null | ((url: string, data: any) => Promise<any>),
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
  const instance: any = (config: any) => {
    captured.retryCalls.push(config);
    return Promise.resolve({ data: { retried: true }, config });
  };
  instance.interceptors = interceptors;
  return {
    default: {
      create: (config: any) => {
        captured.createConfig = config;
        return instance;
      },
      post: (url: string, data: any) => {
        captured.postCalls.push({ url, data });
        if (!captured.postImpl) {
          return Promise.reject(new Error("postImpl not set"));
        }
        return captured.postImpl(url, data);
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

function make401Error(url: string, retry?: boolean) {
  const config: any = { url, headers: { Authorization: "Bearer stale" } };
  if (retry) config._retry = true;
  return { response: { status: 401 }, config };
}

describe("lib/api axios instance", () => {
  let ls: ReturnType<typeof makeLocalStorage>;
  let win: { location: { href: string } };

  beforeEach(() => {
    // NOTE: the interceptor handlers are registered once at module-import time
    // and must NOT be cleared here — tests drive them directly.
    captured.retryCalls = [];
    captured.postCalls = [];
    captured.postImpl = null;
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

    it("clears tokens and redirects to /login on 401 when there is no request to retry", async () => {
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
      expect(captured.postCalls).toHaveLength(0);
    });

    it("does not redirect or clear tokens on non-401 errors", async () => {
      ls.setItem("access_token", "keep");
      const error = { response: { status: 500 }, config: { url: "/employees" } };
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

  describe("silent refresh on 401", () => {
    it("rotates the tokens, retries the original request, and does not redirect", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "r-1");
      captured.postImpl = async (url, data) => {
        expect(url).toBe("/api/v1/auth/refresh");
        expect(data).toEqual({ refresh_token: "r-1" });
        return { data: { access_token: "a-2", refresh_token: "r-2" } };
      };

      const error = make401Error("/employees?page=1");
      const result = await captured.onError[0](error);

      // The original request was retried with the new access token...
      expect(captured.retryCalls).toHaveLength(1);
      expect(captured.retryCalls[0].url).toBe("/employees?page=1");
      expect(captured.retryCalls[0].headers.Authorization).toBe("Bearer a-2");
      // ...and the session was upgraded in place.
      expect(ls.getItem("access_token")).toBe("a-2");
      expect(ls.getItem("refresh_token")).toBe("r-2");
      expect(win.location.href).toBe("");
      expect(result.data.retried).toBe(true);
    });

    it("clears the session and redirects when the refresh itself fails", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "r-dead");
      captured.postImpl = async () => {
        throw new Error("refresh 401");
      };

      const error = make401Error("/employees");
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(captured.postCalls).toHaveLength(1);
      expect(ls.getItem("access_token")).toBeNull();
      expect(ls.getItem("refresh_token")).toBeNull();
      expect(win.location.href).toMatch(/#\/login$/);
      expect(captured.retryCalls).toHaveLength(0);
    });

    it("does not attempt a refresh when no refresh token is stored", async () => {
      ls.setItem("access_token", "stale");
      const error = make401Error("/employees");
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(captured.postCalls).toHaveLength(0);
      expect(win.location.href).toMatch(/#\/login$/);
    });

    it("never refreshes in response to a 401 from /auth/login", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "r-1");
      captured.postImpl = async () => ({ data: { access_token: "a-2", refresh_token: "r-2" } });

      const error = make401Error("/auth/login");
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(captured.postCalls).toHaveLength(0);
      expect(win.location.href).toMatch(/#\/login$/);
    });

    it("never retries a request that already retried once", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "r-1");
      captured.postImpl = async () => ({ data: { access_token: "a-2", refresh_token: "r-2" } });

      const error = make401Error("/employees", true);
      await expect(captured.onError[0](error)).rejects.toBe(error);
      expect(captured.postCalls).toHaveLength(0);
      expect(captured.retryCalls).toHaveLength(0);
      expect(win.location.href).toMatch(/#\/login$/);
    });

    it("runs a single refresh for concurrent 401s (rotation revokes the presented token)", async () => {
      ls.setItem("access_token", "stale");
      ls.setItem("refresh_token", "r-1");
      captured.postImpl = async () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ data: { access_token: "a-2", refresh_token: "r-2" } }), 10),
        );

      const [resA, resB] = await Promise.all([
        captured.onError[0](make401Error("/employees")),
        captured.onError[0](make401Error("/departments")),
      ]);

      // Exactly one rotation despite two concurrent expirations...
      expect(captured.postCalls).toHaveLength(1);
      // ...and both requests were retried with the new token.
      expect(captured.retryCalls).toHaveLength(2);
      for (const cfg of captured.retryCalls) {
        expect(cfg.headers.Authorization).toBe("Bearer a-2");
      }
      expect(resA.data.retried).toBe(true);
      expect(resB.data.retried).toBe(true);
    });
  });

  it("exposes the mock instance as the default export (interceptor wiring ran)", () => {
    expect((api as any).interceptors).toBeDefined();
  });
});
