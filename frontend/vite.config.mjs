import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "node:path";
import { fileURLToPath } from "node:url";

const stubPath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "src/testUtils/reactRouterDomStub.jsx"
);

export default defineConfig({
  plugins: [react(), svgr({ include: "**/*.svg" })],
  // Relative base keeps the bundle deployable under any subpath
  // (replaces CRA's "homepage": "."). Dev/screenshot builds stay on "./";
  // the prod image sets VITE_BASE_PATH=/conference-demo/ so built asset
  // URLs are absolute and correct at any page depth — required for
  // per-conference pages under /conference-demo/<slug>/.
  base: process.env.VITE_BASE_PATH || "./",
  // Keep the CRA output directory name: the Dockerfile copies /app/build
  // and scripts/capture-screenshots.sh serves it.
  build: {
    outDir: "build",
  },
  server: {
    port: 3000,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["@testing-library/jest-dom/vitest"],
    alias: {
      // Tests run against a minimal router stub, same alias as jest's
      // old moduleNameMapper provided.
      "react-router-dom": stubPath,
    },
  },
});
