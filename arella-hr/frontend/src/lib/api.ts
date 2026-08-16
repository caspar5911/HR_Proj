import axios, { type AxiosRequestConfig } from "axios";

/**
 * API base URL.
 * - Same-origin deployments (dev / Docker / nginx proxy): relative "/api/v1"
 * - Static hosts (e.g. GitHub Pages): full URL of the hosted backend, set at
 *   build time via VITE_API_URL (e.g. https://api.example.com/api/v1)
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

/** Axios instance pre-configured with base URL and JWT interceptor. */
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── silent refresh ──────────────────────────────────────────────────────────
// Access tokens are short-lived; refresh tokens live for days. An expired
// access token must not kill an otherwise-healthy session, so on 401 the
// refresh token is exchanged for a fresh pair and the original request is
// retried exactly once.
//
// Two invariants keep this safe:
// - Only ONE caller may rotate: the server revokes a refresh token the moment
//   it is used, so a second concurrent rotation would 401. All 401s therefore
//   await a single shared in-flight refresh promise.
// - The refresh call itself uses the raw axios instance, so its own 401 can
//   never re-enter this interceptor and loop.

type RetryableConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshInFlight: Promise<string | null> | null = null;

function clearSession(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function redirectToLogin(): void {
  clearSession();
  // Hash routing (GitHub Pages): the login route lives in the URL
  // fragment, not the path. BASE_URL is "/" in dev, "/<repo>/" on Pages.
  window.location.href = `${import.meta.env.BASE_URL}#/login`;
}

async function refreshTokens(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;
  try {
    const res = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } },
    );
    const { access_token: access, refresh_token: rotated } = res.data;
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", rotated);
    return access;
  } catch {
    // Revoked/expired/absent refresh token: the session is over.
    return null;
  }
}

async function singleFlightRefresh(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = refreshTokens().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original: RetryableConfig | undefined = error.config;
    const status = error.response?.status;

    // A 401 from /auth/login is just wrong credentials — never "refresh" in
    // response to it, and never retry the login itself.
    const isAuthCall =
      original?.url?.includes("/auth/login") ||
      original?.url?.includes("/auth/refresh");

    if (status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      const newToken = await singleFlightRefresh();
      if (newToken) {
        original.headers = {
          ...original.headers,
          Authorization: `Bearer ${newToken}`,
        };
        return api(original);
      }
    }

    if (status === 401) {
      redirectToLogin();
    }
    return Promise.reject(error);
  }
);

export default api;
