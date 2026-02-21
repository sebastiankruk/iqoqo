import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Vitest configuration for the iqoqo frontend.
 *
 * Uses happy-dom as the DOM environment (fully ESM-compatible, lighter than
 * jsdom). Path alias "@/" mirrors the tsconfig.json paths so that the same
 * import style used in source files works inside test files too.
 */
export default defineConfig({
  plugins: [react()],

  test: {
    environment: "happy-dom",

    // Inject vi, describe, it, expect etc. as globals (no need to import them).
    globals: true,

    // Run the shared setup before every test file.
    setupFiles: ["./vitest.setup.ts"],

    // Pick up all test files from the __tests__ directory.
    include: ["__tests__/**/*.test.{ts,tsx}"],

    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      include: ["components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}", "app/**/*.{ts,tsx}"],
      exclude: ["**/*.d.ts", "**/*.stories.*", "node_modules/**"],
    },
  },

  resolve: {
    alias: {
      // Resolve the "@/" root alias used throughout the codebase.
      "@": path.resolve(__dirname, "."),
    },
  },
});
