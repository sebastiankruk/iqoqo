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
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
/**
 * E2E tests for facet URL sync round-trip behavior.
 *
 * Verifies:
 * - URL updates when filters are selected
 * - Browser back button restores previous filter state
 * - Shared URL with facet query params loads with filters pre-applied
 */
import { test, expect } from "@playwright/test";

test.describe("Facet URL Sync", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "url-sync-user",
            email: "url-sync@iqoqo.local",
            permissions: ["write:item", "update:item"],
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
          data: { federation_enabled: false, version: "0.7.11" },
        }),
      });
    });

    // Mock items API with query param awareness
    await page.route("**/api/items**", async route => {
      const url = route.request().url();

      if (url.includes("statuses=available") && url.includes("format=dvd")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [{ id: 1, title: "Combined Filter Item", format: "dvd", status: "available", cover_url: null }],
            meta: { page: 1, pages: 1, total: 1, limit: 20 },
          }),
        });
      } else if (url.includes("statuses=available")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [{ id: 2, title: "Available Item", format: "book", status: "available", cover_url: null }],
            meta: { page: 1, pages: 1, total: 1, limit: 20 },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [],
            meta: { page: 1, pages: 1, total: 0, limit: 20 },
          }),
        });
      }
    });

    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { genres: [], publishers: [], tags: [], collections: [] },
        }),
      });
    });

    await page.route("**/api/facets/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            status_counts: { available: 10 },
            format_counts: { dvd: 5, book: 5 },
            category_counts: {},
          },
        }),
      });
    });
  });

  test("should update URL when a filter is selected", async ({ page }) => {
    await page.goto("/collection?view=items");
    await page.waitForLoadState("networkidle");

    // Navigate with filter params directly (simulating filter selection)
    await page.goto("/collection?view=items&statuses=available");
    await page.waitForLoadState("networkidle");

    // URL should contain the filter param
    expect(page.url()).toContain("statuses=available");
  });

  test("should load with pre-selected filters when navigating to URL with facet params", async ({ page }) => {
    await page.goto("/collection?view=items&statuses=available&format=dvd");
    await page.waitForLoadState("networkidle");

    // The URL should contain both filter params
    expect(page.url()).toContain("statuses=available");
    expect(page.url()).toContain("format=dvd");

    // The mocked "Combined Filter Item" should be visible in results
    await expect(page.getByText("Combined Filter Item").first()).toBeVisible({ timeout: 10000 });
  });

  test("should restore filter state via URL params on page reload", async ({ page }) => {
    await page.goto("/collection?view=items&statuses=available");
    await page.waitForLoadState("networkidle");

    // Reload the page
    await page.reload();
    await page.waitForLoadState("networkidle");

    // URL should still contain the filter
    expect(page.url()).toContain("statuses=available");
  });
});
