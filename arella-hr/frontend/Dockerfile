# syntax=docker/dockerfile:1

# ── Production build: type-check + bundle with Vite ───────────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Dev server (hot reload; compose bind-mounts the source over /app) ─────
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Production server: nginx serving the static build ─────────────────────
# /api is proxied to the backend service (see nginx.conf), so the browser
# talks to one origin — no CORS, no baked-in API URL.
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
