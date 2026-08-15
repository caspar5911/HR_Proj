import axios from "axios";

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

// On 401, strip the token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      // Hash routing (GitHub Pages): the login route lives in the URL
      // fragment, not the path. BASE_URL is "/" in dev, "/<repo>/" on Pages.
      window.location.href = `${import.meta.env.BASE_URL}#/login`;
    }
    return Promise.reject(error);
  }
);

export default api;