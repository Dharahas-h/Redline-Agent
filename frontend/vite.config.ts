/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/negotiations": "http://localhost:8000",
      "/rounds": "http://localhost:8000",
      "/changes": "http://localhost:8000",
      "/clauses": "http://localhost:8000",
      "/exports": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
