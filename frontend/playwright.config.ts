// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import { defineConfig, devices } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Determine the Python executable to use (check for local virtualenv first)
const hasLocalVenv = fs.existsSync(path.join(__dirname, "../.venv/bin/python"));
const pythonExecutable = hasLocalVenv ? ".venv/bin/python" : "python";

export default defineConfig({
  testDir: "./__tests__/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  // Global per-test timeout: 60s in CI, default in dev
  timeout: process.env.CI ? 60000 : 30000,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    // Navigation timeout: give pages longer to load in CI
    navigationTimeout: 30000,
    actionTimeout: process.env.CI ? 15000 : 5000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        permissions: ["camera"],
        launchOptions: {
          args: [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
          ],
        },
      },
    },
    {
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
      },
    },
    {
      name: "webkit",
      use: {
        ...devices["Desktop Safari"],
      },
    },
  ],
  webServer: [
    {
      command: "NODE_OPTIONS='--no-warnings' npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command:
        "PYTHONUNBUFFERED=1 RATELIMIT_ENABLED=False ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin} FLASK_DEBUG=1 FLASK_APP=app PYTHONPATH=. " +
        pythonExecutable +
        " -m flask run --port 5000",
      url: "http://127.0.0.1:5000/api/health",
      reuseExistingServer: true,
      timeout: 60000,
      cwd: "..",
    },
  ],
});
