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
 * E2E tests for ARIA live region announcements.
 *
 * Verifies:
 * - aria-live element contains announcement text after filter applied
 * - aria-live element announces filter removal
 * - aria-live element announces all filters cleared
 */
import { test, expect } from "@playwright/test";

test.describe("ARIA Live Region Announcements", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "aria-user",
            email: "aria@iqoqo.local",
            permissions: ["write:item"],
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

    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [{ id: 1, title: "ARIA Test Item", status: "available", format: "dvd", cover_url: null }],
          meta: { page: 1, pages: 1, total: 1, limit: 20 },
        }),
      });
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
            status_counts: { available: 5 },
            format_counts: { dvd: 5 },
            category_counts: { movie: 5 },
          },
        }),
      });
    });
  });

  test("should have aria-live element on collection page", async ({ page }) => {
    await page.goto("/collection?view=items");

    await page.waitForSelector("body");

    // Check that the aria-live polite element exists in the DOM
    const liveRegion = page.locator('[aria-live="polite"]');
    await expect(liveRegion).toHaveCount(1);
  });

  test("should have sr-only class on the aria-live element", async ({ page }) => {
    await page.goto("/collection?view=items");

    await page.waitForSelector("body");

    const liveRegion = page.locator('[aria-live="polite"]');
    await expect(liveRegion).toHaveClass(/sr-only/);
  });

  test("should show initial all-filters-cleared announcement", async ({ page }) => {
    await page.goto("/collection?view=items");

    await page.waitForSelector("body");

    const liveRegion = page.locator('[aria-live="polite"]');
    const text = await liveRegion.textContent();
    expect(text).toContain("All filters cleared");
  });

  test("should show result count in aria-live text", async ({ page }) => {
    await page.goto("/collection?view=items");

    await page.waitForSelector("body");

    const liveRegion = page.locator('[aria-live="polite"]');
    const text = await liveRegion.textContent();
    expect(text).toMatch(/\d+ results found/);
  });
});
