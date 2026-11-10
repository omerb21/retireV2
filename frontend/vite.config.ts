import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === "test" ? [{
      name: "retire-v2-local-browser-test-identity",
      configureServer(server: import("vite").ViteDevServer) {
        server.middlewares.use("/__retire_v2_test_identity", (req, res, next) => {
          if (req.method !== "GET") return next();
          const host = req.headers.host;
          if (host !== "127.0.0.1:5174") {
            res.statusCode = 403;
            res.end("LOOPBACK_TEST_ONLY");
            return;
          }
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.setHeader("Cache-Control", "no-store");
          res.end(JSON.stringify({ service: "RETIRE_V2_FRONTEND", mode: "test", port: 5174 }));
        });
      },
    }] : []),
  ],
  server: {
    port: mode === "test" ? 5174 : undefined,
    strictPort: mode === "test",
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
}));
