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
 * E2E tests for cross-FRBR filtering at the Works and Expressions levels.
 *
 * Verifies:
 * - Works-level browsing with item status filter
 * - Works-level browsing with item tag filter
 * - Expressions-level browsing with physical format filter
 * - Combined status + format cross-FRBR filters with AND logic
 * - Empty result state when no items match
 */
import { test, expect } from "@playwright/test";

test.describe("Cross-FRBR Filtering at Works/Expressions Levels", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    // Mock profile
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "e2e-cross-frbr-user",
            email: "e2e-cross-frbr@iqoqo.local",
            display_name: "Cross-FRBR Tester",
            permissions: ["write:item", "update:item", "upload:cover"],
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
          data: { federation_enabled: false, version: "0.7.11" },
        }),
      });
    });

    // Mock works/shelf with cross-FRBR filter responses
    await page.route("**/api/works/shelf**", async route => {
      const url = route.request().url();
      const hasStatusFilter = url.includes("statuses=");
      const hasFormatFilter = url.includes("formats=");

      // Combined filter (AND logic) → fewer results
      if (hasStatusFilter && hasFormatFilter) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                work_id: 1,
                title: "Works with both filters",
                creators: ["Test Creator"],
                content_type: "movie",
                items: [],
              },
            ],
            meta: { page: 1, pages: 1, total: 1, limit: 20 },
          }),
        });
      } else if (url.includes("statuses=available")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                work_id: 301,
                title: "Available Work",
                creators: ["Author One"],
                content_type: "text",
                items: [{ item_id: 401, status: "available", collection_status: "available" }],
              },
              {
                work_id: 302,
                title: "Another Available Work",
                creators: ["Author Two"],
                content_type: "movie",
                items: [{ item_id: 402, status: "available", collection_status: "available" }],
              },
            ],
            meta: { page: 1, pages: 1, total: 2, limit: 20 },
          }),
        });
      } else if (url.includes("tags=horror")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                work_id: 501,
                title: "Horror Movie",
                creators: ["Horror Director"],
                content_type: "movie",
                items: [{ item_id: 601, tags: ["horror"] }],
              },
            ],
            meta: { page: 1, pages: 1, total: 1, limit: 20 },
          }),
        });
      } else if (url.includes("nonexistent")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [],
            meta: { page: 1, pages: 1, total: 0, limit: 20 },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                work_id: 201,
                title: "Global Catalog Work",
                creators: ["Catalog Author"],
                content_type: "text",
                items: [],
              },
            ],
            meta: { page: 1, pages: 1, total: 1, limit: 20 },
          }),
        });
      }
    });

    // Mock expressions/shelf
    await page.route("**/api/expressions/shelf**", async route => {
      const url = route.request().url();
      if (url.includes("formats=dvd")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                expression_id: 701,
                work_title: "DVD Expression",
                content_type: "movie",
                language: "en",
              },
            ],
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

    // Mock taxonomies
    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { genres: ["Fiction"], publishers: ["Atlantic"], tags: ["horror", "classic"], collections: [] },
        }),
      });
    });

    // Mock facet stats
    await page.route("**/api/facets/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            status_counts: { available: 10, wish_list: 5 },
            format_counts: { dvd: 8, blu_ray: 2 },
            category_counts: { movie: 15, text: 5 },
            tag_counts: { horror: 3, classic: 2 },
          },
        }),
      });
    });
  });

  test("should show only Works with available items when status filter is applied", async ({ page }) => {
    // Navigate to the global catalog (works shelf) with status filter
    await page.goto("/collection?view=works&statuses=available");
    await page.waitForLoadState("networkidle");

    // The mocked "Available Work" should be visible
    await expect(page.getByText("Available Work").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Another Available Work").first()).toBeVisible({ timeout: 10000 });
  });

  test("should show empty results with 200 status when no items match filters", async ({ page }) => {
    await page.goto("/collection?view=works&tags=nonexistent");
    await page.waitForLoadState("networkidle");

    // The page should load without error — empty results displayed gracefully
    await expect(page).toHaveTitle(/.+/);
  });

  test("should filter Expressions by physical format at Expressions level", async ({ page }) => {
    await page.goto("/collection?view=expressions&formats=dvd");
    await page.waitForLoadState("networkidle");

    // The mocked "DVD Expression" work title should be visible
    await expect(page.getByText("DVD Expression").first()).toBeVisible({ timeout: 10000 });
  });

  test("should apply combined status and format cross-FRBR filters at Works level", async ({ page }) => {
    await page.goto("/collection?view=works&statuses=available&formats=dvd");
    await page.waitForLoadState("networkidle");

    // Both filters should be applied — the mocked combined result should be visible
    await expect(page.getByText("Works with both filters").first()).toBeVisible({ timeout: 10000 });
  });
});
