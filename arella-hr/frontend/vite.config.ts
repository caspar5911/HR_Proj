import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Where the dev server forwards /api requests to.
//  - Local (no Docker): the backend on the host — default http://localhost:8000
//  - Docker dev: the backend service, injected via API_PROXY_TARGET
//    (see docker-compose.yml). Inside the frontend container `localhost`
//    is NOT the backend, so the service name must be used instead.
const apiProxyTarget = process.env.API_PROXY_TARGET || "http://localhost:8000";

// Public base path the built assets are served from.
//  - Dev / Docker / nginx: "/" (default)
//  - GitHub Pages project site: "/<repo>/", injected via VITE_BASE_PATH
//    (see .github/workflows/deploy-pages.yml). Vite rewrites every emitted
//    asset URL with this prefix so the build works from a sub-path.
const base = process.env.VITE_BASE_PATH || "/";

export default defineConfig({
  base,
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
