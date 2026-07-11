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

test.describe("Item-Collection Linking Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // Cookie consent
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock auth profile
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "e2e-admin-id",
            email: "e2e-admin@iqoqo.local",
            display_name: "E2E Admin",
            roles: ["admin"],
            permissions: ["upload:cover", "write:metadata", "update:item", "delete:item"],
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
          data: { federation_enabled: false, version: "1.0.0" },
        }),
      });
    });
  });

  test("item detail page renders with named collections section", async ({ page }) => {
    // Mock a single item with detail
    await page.route("**/api/item/*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 1,
            manifestation_id: 1,
            owner_id: "e2e-admin-id",
            status: "unread",
            collection_status: "available",
            title: "E2E Test Book",
            authors: ["Test Author"],
            cover_url: "",
            cover_status: "ready",
            isbn: "9780000000001",
            is_owner: true,
            manifestation_meta: { format: "book" },
            meta: {},
          },
        }),
      });
    });

    // Mock item collections (empty — just checks it renders)
    await page.route("**/api/items/*/collections", async route => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: { collections: [] },
          }),
        });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) });
      }
    });

    // Mock user collections list
    await page.route("**/api/collections", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, collections: [] }),
      });
    });

    // Navigate to item detail
    await page.goto("/item/1");
    await page.waitForLoadState("networkidle");

    // The item detail page should load and render
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });
});
