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
import { test, expect } from "@playwright/test";

test.describe("Phase 3 DevOps & UI Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock Profile to bypass login redirects
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "admin-id",
            email: "admin@iqoqo.local",
            display_name: "Admin User",
            roles: ["admin"],
            permissions: ["config:internal", "write:metadata"],
          },
        },
      })
    );

    // Mock Config
    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false, version: "0.6.0" } },
      })
    );

    // Mock Settings
    await page.route("**/v1/admin/settings*", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            MAINTENANCE_MODE: { value: "false", source: "db" },
            IQOQO_KNOWN_JUNK_PHASHES: { value: "", source: "db" },
          },
        },
      })
    );
  });

  test("Landing page has functional GitHub link", async ({ page }) => {
    // Un-mock profile or mock as 401 to see the landing page Hero
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 401,
        json: { success: false, error: "Unauthorized" },
      })
    );

    await page.goto("/");
    const githubLink = page.getByRole("link", { name: "GitHub", exact: true });
    await expect(githubLink).toBeVisible();
    await expect(githubLink).toHaveAttribute("href", "https://github.com/sebastiankruk/iqoqo");
    await expect(githubLink).toHaveAttribute("target", "_blank");
  });

  test("Admin internal settings show Maintenance Mode toggle", async ({ page }) => {
    // Note: This requires admin login which is mocked in beforeEach
    await page.goto("/admin/settings?tab=instance");

    // Check if the Maintenance Mode card exists
    await expect(page.getByText("Maintenance Mode")).toBeVisible();
    await expect(page.locator("select")).toBeVisible();
  });
});
