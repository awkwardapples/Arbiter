/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const API = process.env.ARBITER_API_URL ?? "http://localhost:8000";
// Every API prefix the console calls; the dev server forwards them to FastAPI.
const PROXIED = [
  "/runs",
  "/cases",
  "/contracts",
  "/health",
  "/vendors",
  "/questions",
  "/memory",
  "/audit",
  "/eval",
  "/registry",
  "/usl",
  "/evidence",
  "/recordings",
  "/agents",
  "/openapi.json",
];

export default defineConfig({
  base: "/console/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(PROXIED.map((p) => [p, { target: API, changeOrigin: true }])),
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
