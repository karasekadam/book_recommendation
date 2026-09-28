import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Requests to /api/* are forwarded to Flask, so the browser sees one origin (no CORS needed)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
