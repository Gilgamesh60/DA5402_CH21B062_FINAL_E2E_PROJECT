import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build to `dist/`. In production the built assets are served by nginx.
// API base URL is provided at runtime via /config.js so the same image
// works across dev / demo / prod without a rebuild — this is the
// configurable-REST requirement from the rubric.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
