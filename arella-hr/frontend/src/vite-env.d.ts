/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Full API base URL, including the /api/v1 prefix.
   * Leave unset for same-origin deployments (dev / Docker / nginx proxy).
   * Set it when building for a static host (e.g. GitHub Pages) that serves
   * the frontend from a different origin than the backend, e.g.
   *   VITE_API_URL=https://your-backend.example.com/api/v1
   */
  readonly VITE_API_URL?: string;
}
