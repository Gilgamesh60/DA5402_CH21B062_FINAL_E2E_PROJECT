# Phase 7: real React frontend. Two-stage build.

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

# Copy manifests first to leverage layer caching
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---- Runtime stage ----
FROM nginx:1.27-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# nginx config (proxies /api -> api service and serves SPA)
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# entrypoint rewrites /config.js with live env vars so one image works
# across dev / demo / prod without a rebuild
COPY docker/frontend/entrypoint.sh /docker-entrypoint.d/40-ssa-config.sh
RUN chmod +x /docker-entrypoint.d/40-ssa-config.sh

EXPOSE 80
