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
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Admin User Management & RBAC Workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock Admin Auth Profile with permissions
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "admin-id",
            email: "admin@iqoqo.local",
            display_name: "System Admin",
            roles: ["admin"],
            permissions: [
              "config:external_apis",
              "config:federation",
              "config:affiliate",
              "config:internal",
              "read:users",
              "write:users",
              "read:roles",
              "write:roles",
            ],
          },
        },
      })
    );

    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false, version: packageJson.version } },
      })
    );

    // Mock users API
    await page.route("**/v1/admin/users*", async route => {
      await route.fulfill({
        status: 200,
        json: {
          success: true,
          data: [
            {
              id: "target-user-123",
              email: "jane.doe@example.com",
              display_name: "Jane Doe",
              roles: ["user"],
              is_active: true,
            },
          ],
          meta: { total: 1, page: 1, pages: 1 },
        },
      });
    });
  });

  test("Should load admin settings page", async ({ page }) => {
    await page.goto("/admin/settings?tab=users");
    await expect(page.locator("main")).toBeVisible();
  });
});
