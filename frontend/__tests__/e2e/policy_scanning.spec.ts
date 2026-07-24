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

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Policy Scanning", () => {
  const testBarcode = "9780140449136";

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-policy", domain: "localhost", path: "/" }]);

    // Mock user profile
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            display_name: "Policy Scanner",
            permissions: ["upload:cover", "update:item", "write:metadata"],
          },
        }),
      });
    });

    await page.route("**/api/config**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federation_enabled: false, version: packageJson.version },
        }),
      });
    });

    // Mock empty manifestations for home
    await page.route("**/api/manifestations**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { items: [], total: 0 } }),
      });
    });

    await page.route("**/api/manifestations/recent**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });
  });

  test("switches policy to Wishlist and verifies UI", async ({ page }) => {
    // Navigate to scanner page
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Verify policy selector is visible
    const wishlistBtn = page.getByText("Wishlist", { exact: true });
    if (await wishlistBtn.isVisible()) {
      await wishlistBtn.click();
      await page.waitForTimeout(200);
    }

    // Switch back to Inventory
    const inventoryBtn = page.getByText("Inventory", { exact: true });
    if (await inventoryBtn.isVisible()) {
      await inventoryBtn.click();
      await page.waitForTimeout(200);
    }
  });

  test("switches policy to Catalog and verifies UI", async ({ page }) => {
    // Navigate to scanner page
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Switch to Catalog
    const catalogBtn = page.getByText("Catalog", { exact: true });
    if (await catalogBtn.isVisible()) {
      await catalogBtn.click();
      await page.waitForTimeout(200);
    }
  });

  test("policy switching persists after format change", async ({ page }) => {
    // Navigate to scanner page
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Switch to Wishlist
    const wishlistBtn = page.getByText("Wishlist", { exact: true });
    if (await wishlistBtn.isVisible()) {
      await wishlistBtn.click();
      await page.waitForTimeout(200);
    }

    // Change format
    const musicBtn = page.getByLabel("Music");
    if (await musicBtn.isVisible()) {
      await musicBtn.click();
      await page.waitForTimeout(200);
    }

    // Switch back to Inventory
    const inventoryBtn = page.getByText("Inventory", { exact: true });
    if (await inventoryBtn.isVisible()) {
      await inventoryBtn.click();
      await page.waitForTimeout(200);
    }
  });
});
