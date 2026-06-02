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
// frontend/__tests__/e2e/mobile_catalog_navigation.spec.ts

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Mobile Catalog Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Dismiss cookie consent
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock profile
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            display_name: "Test User",
            roles: ["user"],
            permissions: ["upload:cover", "update:item", "write:metadata"],
          },
        }),
      });
    });

    // Mock config
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
  });

  test("should navigate through FRBR catalog levels on mobile view", async ({ page }) => {
    // 1. Mock items to return a simple book
    await page.route("**/api/items?**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 101,
              title: "Mobile Catalog Book",
              authors: ["Author Mobile"],
              status: "reading",
              collection_status: "available",
              is_owner: true,
              manifestation: {
                id: 201,
                title: "Mobile Catalog Book",
                format: "book",
                cover_url: null,
              },
            },
          ],
          pagination: { page: 1, per_page: 10, total: 1, pages: 1 },
        }),
      });
    });

    // Mock item detail endpoint
    await page.route("**/api/items/101", async route => {
      const url = route.request().url();
      if (url.endsWith("/logs")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: [] }),
        });
      }
      if (url.includes("/loan-status")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: null }),
        });
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 101,
            owner_id: "test-user-id",
            status: "reading",
            collection_status: "available",
            title: "Mobile Catalog Book",
            meta: { format: "book" },
            manifestation_id: 201,
            manifestation_meta: { format: "book" },
            work: { id: 301, title: "Mobile Catalog Book" },
            expression: { id: 401 },
          },
        }),
      });
    });

    // Mock manifestation endpoint
    await page.route("**/api/manifestations/201", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 201,
            expression_id: 401,
            work_id: 301,
            title: "Mobile Catalog Book",
            isbn13: "9780134685991",
            publisher: "Mobile Press",
            year: 2026,
            cover_url: null,
            user_owns: true,
            item_id: 101,
            owner_count: 1,
            meta: { Format: "book" },
          },
        }),
      });
    });

    // Mock manifestation parts endpoint (Series)
    await page.route("**/api/works/301/parts", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    // Mock social review feeds
    await page.route("**/api/feedback**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    // 2. Load dashboard
    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // Verify item card is displayed
    const card = page.locator('[data-testid="item-card"]');
    await expect(card).toBeVisible();
    await expect(page.getByText("Mobile Catalog Book")).toBeVisible();

    // 3. Click card to open Item detail page
    await card.click();
    await expect(page).toHaveURL(/.*\/item\?id=101/);

    // Verify Item Page loaded
    await expect(page.getByText("Availability & Condition")).toBeVisible();
    await expect(page.getByText("Mobile Catalog Book").first()).toBeVisible();

    // 4. Click Manifestation detail link (Edition)
    const manifestationLink = page.getByRole("link", { name: "Edition details" }).first();
    if (await manifestationLink.isVisible()) {
      await manifestationLink.click();
    } else {
      // Fallback: Click on Manifestation metadata link
      await page.goto("/manifestation?id=201");
    }

    await expect(page).toHaveURL(/.*\/manifestation\?id=201/);

    // Verify Manifestation page loaded
    await expect(page.getByText("Publication Details")).toBeVisible();
    await expect(page.getByText("9780134685991")).toBeVisible();

    // 5. Back navigation works
    await page.goBack();
    await expect(page).toHaveURL(/.*\/item\?id=101/);

    await page.goBack();
    await expect(page).toHaveURL(/.*\/collection/);
  });

  test("should verify bottom navigation tabs exist on mobile viewport", async ({ page }) => {
    // 1. Mock items empty
    await page.route("**/api/items?**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
          pagination: { page: 1, per_page: 10, total: 0, pages: 1 },
        }),
      });
    });

    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // Mobile nav bar checks
    const bottomNav = page.locator("nav");
    await expect(bottomNav).toBeVisible();

    // Check for standard navigation links
    const homeLink = bottomNav.getByRole("link", { name: /home|discover/i });
    const collectionLink = bottomNav.getByRole("link", { name: /collection/i });
    const scanLink = bottomNav.getByRole("link", { name: /scan/i });

    await expect(collectionLink).toBeVisible();
    await expect(scanLink).toBeVisible();
  });
});
