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

test.describe("Admin User Management & RBAC Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Pre-seed localStorage
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // 2. Mock Admin Auth Profile
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
            permissions: ["*"],
          },
        },
      })
    );

    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false, version: "0.4.0" } },
      })
    );

    // 3. Intercept initial Users GET request
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

    await page.goto("/admin/settings");
  });

  test("Should display data table and modify permissions in RBAC sheet", async ({ page }) => {
    // Wait for the data table
    await expect(page.getByText("jane.doe@example.com")).toBeVisible();
    await expect(page.getByText("Jane Doe")).toBeVisible();
    await expect(page.getByText("Active").first()).toBeVisible();

    // Click the row to open the RBAC Sheet
    await page.getByText("jane.doe@example.com").click();

    // Verify Sheet UI renders
    await expect(page.getByText("User Access Control")).toBeVisible();
    await expect(page.getByText("Active Account")).toBeVisible();

    // Intercept PUT request to assert valid payload construction
    let putRequestData: { is_active: boolean; roles: string[] } | null = null;
    await page.route("**/v1/admin/users/target-user-123", async route => {
      putRequestData = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "target-user-123",
            email: "jane.doe@example.com",
            display_name: "Jane Doe",
            roles: ["user", "custodian"],
            is_active: true,
          },
        },
      });
    });

    // Assign new 'custodian' role via checkbox
    await page.getByLabel("custodian").check();

    // Save
    await page.getByRole("button", { name: "Save Permissions" }).click();

    // Verify Sheet slides away
    await expect(page.getByText("User Access Control")).not.toBeVisible();

    // Verify request payload was exact
    expect(putRequestData).toEqual({
      is_active: true,
      roles: ["user", "custodian"],
    });
  });
});
