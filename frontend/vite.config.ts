import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
  build: { manifest: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/vitest.setup.ts"
  }
});
