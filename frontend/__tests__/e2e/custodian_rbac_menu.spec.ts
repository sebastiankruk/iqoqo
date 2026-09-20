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
/**
 * E2E tests for custodian RBAC menu access.
 *
 * Regression test for: Custodian role no longer has access to Administration menu
 *
 * These tests verify that:
 * 1. Custodian users can see the Administration menu
 * 2. Users with custodian permissions (colon format) can see the menu
 * 3. Regular users without custodian permissions cannot see the menu
 * 4. The menu links to the correct admin settings page
 */

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

/**
 * Helper function to set up custodian user profile mock
 */
async function mockCustodianProfile(
  page: import("@playwright/test").Page,
  options: {
    roles?: string[];
    permissions?: string[];
    email?: string;
    displayName?: string;
  } = {}
) {
  const {
    roles = ["user", "custodian"],
    permissions = ["write:metadata", "read:metadata", "escalate:resolve"],
    email = "custodian@iqoqo.local",
    displayName = "Test Custodian",
  } = options;

  await page.route("**/api/profile**", route =>
    route.fulfill({
      status: 200,
      json: {
        success: true,
        data: {
          id: "custodian-id",
          email,
          display_name: displayName,
          roles,
          permissions,
        },
      },
    })
  );
}

/**
 * Helper function to set up regular user profile mock
 */
async function mockRegularUserProfile(page: import("@playwright/test").Page) {
  await page.route("**/api/profile**", route =>
    route.fulfill({
      status: 200,
      json: {
        success: true,
        data: {
          id: "regular-user-id",
          email: "regular@iqoqo.local",
          display_name: "Regular User",
          roles: ["user"],
          permissions: ["read:owners"],
        },
      },
    })
  );
}

/**
 * Helper function to set up admin user profile mock
 */
async function mockAdminProfile(page: import("@playwright/test").Page) {
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
}

test.describe("Custodian RBAC Menu Access - Regression Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page.context().addCookies([
      { name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" },
    ]);

    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: { federation_enabled: false, version: packageJson.version },
        },
      })
    );
  });

  test.describe("Positive cases - Custodian should see Administration menu", () => {
    test("custodian user with custodian role sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user", "custodian"],
        permissions: [],
      });

      await page.goto("/");

      // Click on user menu
      await page.getByLabel("User menu").click();

      // Verify Administration menu item is visible
      const menu = page.getByRole("menu");
      await expect(menu).toBeVisible();

      const adminMenuItem = menu.getByText("Administration");
      await expect(adminMenuItem).toBeVisible();

      // Verify it links to admin settings
      const adminLink = menu.getByRole("link", { name: "Administration" });
      await expect(adminLink).toHaveAttribute("href", "/admin/settings");
    });

    test("user with write:metadata permission sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user"],
        permissions: ["write:metadata"],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });

    test("user with edit:cover permission sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user"],
        permissions: ["edit:cover"],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });

    test("user with escalate:resolve permission sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user"],
        permissions: ["escalate:resolve"],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });

    test("user with read:metadata permission sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user"],
        permissions: ["read:metadata"],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });

    test("user with multiple custodian permissions sees Administration menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["user"],
        permissions: ["write:metadata", "edit:cover", "escalate:resolve", "read:metadata"],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });

    test("admin user sees Administration menu", async ({ page }) => {
      await mockAdminProfile(page);

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });
  });

  test.describe("Negative cases - Regular users should NOT see Administration menu", () => {
    test("regular user without custodian permissions does not see Administration menu", async ({
      page,
    }) => {
      await mockRegularUserProfile(page);

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu).toBeVisible();

      // Administration should NOT be visible
      await expect(menu.getByText("Administration")).not.toBeVisible();
    });

    test("user with only non-custodian permissions does not see Administration menu", async ({
      page,
    }) => {
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-id",
              email: "user@iqoqo.local",
              display_name: "Regular User",
              roles: ["user"],
              permissions: ["read:owners", "write:item", "delete:item"],
            },
          },
        })
      );

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).not.toBeVisible();
    });
  });

  test.describe("Regression tests - Permission format validation", () => {
    test("underscore format permissions should NOT grant access (regression)", async ({ page }) => {
      // This is the critical regression test
      // The bug was that the code checked for underscore format instead of colon format
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-id",
              email: "user@iqoqo.local",
              display_name: "User with Wrong Format",
              roles: ["user"],
              permissions: ["write_metadata", "edit_cover", "escalate_resolve"], // Wrong format!
            },
          },
        })
      );

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      // Should NOT see Administration with underscore format
      await expect(menu.getByText("Administration")).not.toBeVisible();
    });

    test("mixed format permissions should only grant access for colon format", async ({ page }) => {
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-id",
              email: "user@iqoqo.local",
              display_name: "User with Mixed Format",
              roles: ["user"],
              permissions: ["write_metadata", "edit:cover"], // Mixed format
            },
          },
        })
      );

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      // Should see Administration because edit:cover is in colon format
      await expect(menu.getByText("Administration")).toBeVisible();
    });
  });

  test.describe("Navigation tests", () => {
    test("clicking Administration menu navigates to admin settings", async ({ page }) => {
      await mockCustodianProfile(page);

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      const adminLink = menu.getByRole("link", { name: "Administration" });

      // Click the link
      await adminLink.click();

      // Verify navigation
      await expect(page).toHaveURL(/.*\/admin\/settings/);
    });

    test("custodian can access admin settings page directly", async ({ page }) => {
      await mockCustodianProfile(page);

      // Navigate directly to admin settings
      await page.goto("/admin/settings");

      // Verify page loads (main content should be visible)
      await expect(page.locator("main")).toBeVisible();
    });
  });

  test.describe("Edge cases", () => {
    test("user with empty permissions array and no custodian role does not see menu", async ({
      page,
    }) => {
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-id",
              email: "user@iqoqo.local",
              display_name: "User",
              roles: ["user"],
              permissions: [],
            },
          },
        })
      );

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).not.toBeVisible();
    });

    test("user with undefined permissions does not see menu", async ({ page }) => {
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-id",
              email: "user@iqoqo.local",
              display_name: "User",
              roles: ["user"],
              // permissions field is missing
            },
          },
        })
      );

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).not.toBeVisible();
    });

    test("user with custodian role and no permissions still sees menu", async ({ page }) => {
      await mockCustodianProfile(page, {
        roles: ["custodian"],
        permissions: [],
      });

      await page.goto("/");
      await page.getByLabel("User menu").click();

      const menu = page.getByRole("menu");
      await expect(menu.getByText("Administration")).toBeVisible();
    });
  });
});
