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

test.describe("Admin Roles Management Workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock Admin Auth Profile
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

    // Mock roles endpoint with member counts
    await page.route("**/v1/admin/roles", async route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: [
            { id: 1, name: "admin", is_protected: true, member_count: 1 },
            { id: 2, name: "user", is_protected: true, member_count: 3 },
            { id: 3, name: "custodian", is_protected: false, member_count: 1 },
          ],
        },
      })
    );

    // Mock permissions endpoint
    await page.route("**/v1/admin/permissions", async route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: [
            { id: 1, name: "delete:item", description: "Allow deletion of items" },
            { id: 2, name: "regenerate:cover", description: "Allow regenerating covers" },
          ],
        },
      })
    );

    // Mock role permissions endpoint
    await page.route("**/v1/admin/roles/3/permissions", async route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: { role_id: 3, role_name: "custodian", permission_ids: [1] },
        },
      })
    );
  });

  test("Should display roles and expand to show permissions", async ({ page }) => {
    await page.goto("/admin/groups");

    // Wait for page to load
    await expect(page.getByRole("heading", { name: "Roles Management" })).toBeVisible();

    // Verify roles are displayed (use role button which contains the role name)
    await expect(page.getByRole("button", { name: /admin/ }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /user/ }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /custodian/ }).first()).toBeVisible();

    // Verify Protected badge is shown
    await expect(page.getByText("Protected").first()).toBeVisible();

    // Click on custodian role to expand - use the h3 heading specifically
    await page.locator("h3", { hasText: "custodian" }).click();

    // Verify permissions panel appears
    await expect(page.getByText("delete:item")).toBeVisible();
  });

  test("Should show Add Role button and open modal", async ({ page }) => {
    await page.goto("/admin/groups");

    await expect(page.getByText("Add Role")).toBeVisible();

    // Click Add Role
    await page.getByText("Add Role").click();

    // Modal should appear
    await expect(page.getByText("Add New Role")).toBeVisible();

    // Close modal
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Add New Role")).not.toBeVisible();
  });
});
