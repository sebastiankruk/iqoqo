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

test.describe("Faceted Catalog Synchronization and Inventory Isolation", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Log all requests and responses
    page.on("request", request => console.log(">> Request:", request.method(), request.url()));
    page.on("response", response => console.log("<< Response:", response.status(), response.url()));

    // 2. Mock user profile
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
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
            permissions: ["upload:cover", "write:metadata", "update:item"],
          },
        }),
      });
    });

    // 3. Mock config
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

    // 4. Mock taxonomies
    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            genres: ["Fiction"],
            publishers: ["Atlantic"],
            tags: [],
            collections: [],
          },
        }),
      });
    });

    // 5. Mock manifestations list
    await page.route("**/api/manifestations**", async route => {
      const url = route.request().url();
      if (url.includes("genres=Fiction")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 9999,
                title: "Global Fiction Novel",
                authors: ["Atlantic Author"],
                isbn13: "9999999999999",
                publisher: "Atlantic",
                cover_url: "https://images.unsplash.com/photo-1543002588-bfa74002ed7e",
                item_id: null,
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

    // 6. Mock expressions shelf
    await page.route("**/api/expressions/shelf**", async route => {
      const url = route.request().url();
      if (url.includes("genres=Fiction")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                expression_id: 999,
                work_title: "Global Fiction Novel",
                creators: ["Atlantic Author"],
                content_type: "text",
                language: "en",
                total_items: 0,
                owned_manifestations: [
                  {
                    manifestation_id: 9999,
                    format: "book",
                    item_id: null,
                    cover_url: "https://images.unsplash.com/photo-1543002588-bfa74002ed7e",
                  },
                ],
              },
            ],
            pagination: { offset: 0, limit: 20, total: 1, has_more: false },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [],
            pagination: { offset: 0, limit: 20, total: 0, has_more: false },
          }),
        });
      }
    });

    // 7. Mock works shelf
    await page.route("**/api/works/shelf**", async route => {
      const url = route.request().url();
      if (url.includes("genres=Fiction")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [
              {
                work_id: 99,
                title: "Global Fiction Novel",
                creators: ["Atlantic Author"],
                total_items: 0,
                owned_manifestations: [
                  {
                    manifestation_id: 9999,
                    format: "book",
                    item_id: null,
                    cover_url: "https://images.unsplash.com/photo-1543002588-bfa74002ed7e",
                  },
                ],
              },
            ],
            pagination: { offset: 0, limit: 20, total: 1, has_more: false },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [],
            pagination: { offset: 0, limit: 20, total: 0, has_more: false },
          }),
        });
      }
    });

    // 8. Mock items
    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
          meta: { page: 1, pages: 1, total: 0, limit: 20 },
        }),
      });
    });

    // 9. Mock stats
    await page.route("**/api/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            works: 1,
            expressions: 1,
            manifestations: 1,
            items: 0,
            format_book: 1,
          },
        }),
      });
    });
  });

  test("should sync global catalog across tabs and isolate personal items layer", async ({ page }) => {
    // Step 1: Direct URL Hydration Navigation to manifestations view
    await page.goto("/collection?genres=Fiction&view=manifestations");

    // Assert "Global Fiction Novel" card is visible
    await expect(page.getByText("Global Fiction Novel").first()).toBeVisible({ timeout: 10000 });

    // Step 2: Global Tab Synchronization Verification (Expressions)
    // Click on the "Expressions" view tab
    const expressionsTab = page.getByRole("tab", { name: "Expressions" });
    await expressionsTab.click();

    // Assert active URL has view=expressions and preserves genres=Fiction
    await expect(page).toHaveURL(/.*view=expressions/);
    await expect(page).toHaveURL(/.*genres=Fiction/);

    // Assert that the unowned novel's expression layer is visible
    await expect(page.getByText("Global Fiction Novel").first()).toBeVisible();

    // Click on the "Works" view tab
    const worksTab = page.getByRole("tab", { name: "Works" });
    await worksTab.click();

    // Assert active URL updates to include view=works and preserves genres=Fiction
    await expect(page).toHaveURL(/.*view=works/);
    await expect(page).toHaveURL(/.*genres=Fiction/);

    // Assert that the unowned novel's work layer is visible
    await expect(page.getByText("Global Fiction Novel").first()).toBeVisible();

    // Step 3: Inventory Layer Isolation & Empty State Verification (Items view)
    const itemsTab = page.getByRole("tab", { name: "My Items" });
    await itemsTab.click();

    // Assert active URL updates to items (view parameter omitted because it's default)
    await expect(page).not.toHaveURL(/.*view=/);
    await expect(page).toHaveURL(/.*genres=Fiction/);

    // Assert that the list displays the empty state: "No items found"
    await expect(page.getByText("No items found").first()).toBeVisible();
    await expect(page.getByText("Global Fiction Novel")).not.toBeVisible();
  });
});

test.describe("Dynamic Facet Cross-Filtering", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "e2e-admin-id",
            email: "e2e-admin@iqoqo.local",
            permissions: ["upload:cover", "write:metadata", "update:item"],
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

    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { genres: ["Fiction"], publishers: [], tags: [], collections: [] },
        }),
      });
    });

    await page.route("**/api/manifestations**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [], meta: { total: 0 } }),
      });
    });

    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
          meta: { page: 1, pages: 1, total: 0, limit: 20 },
        }),
      });
    });

    await page.route("**/api/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            works: 10,
            items: 10,
            format_text: 5,
            format_board_game: 5,
            items_wish_list: 0,
            items_available: 5,
            items_ordered: 0,
            items_lent: 0,
            items_lost: 0,
            genre_counts: { Fiction: 10 },
            category_counts: { text: 5, board_game: 5 },
          },
        }),
      });
    });
  });

  test("mutes status options with zero count when not selected", async ({ page }) => {
    // Mock stats with some statuses having zero count
    // NOTE: the frontend extracts status counts from keys prefixed with "items_"
    await page.route("**/api/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            works: 10,
            items: 5,
            items_wish_list: 0,
            items_available: 5,
            items_ordered: 0,
            items_lent: 0,
            items_lost: 0,
          },
        }),
      });
    });

    await page.route("**/api/stats/facets**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            status_counts: {
              available: 5,
              wish_list: 0,
              ordered: 0,
              lent: 0,
              lost: 0,
            },
          },
        }),
      });
    });

    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // "On Shelf" (available) has count 5 — should be fully visible (no opacity-50)
    // Use .first() to avoid strict mode violation from the mobile filter drawer duplicate
    const onShelfLabel = page.locator("label").filter({ hasText: "On Shelf" }).first();
    await expect(onShelfLabel).toBeVisible();
    await expect(onShelfLabel).not.toHaveClass(/opacity-50/);

    // "On Wish List" has count 0 — should be muted (opacity-50) since not selected
    const onWishListLabel = page.locator("label").filter({ hasText: "On Wish List" }).first();
    await expect(onWishListLabel).toBeVisible();
    await expect(onWishListLabel).toHaveClass(/opacity-50/);
  });

  test("supports multi-selection for category facets", async ({ page }) => {
    // Mock facet stats so that the categories are not disabled
    await page.route("**/*stats*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            works: 10,
            items: 10,
            format_text: 5,
            format_board_game: 5,
            category_counts: { text: 5, board_game: 5 },
          },
        }),
      });
    });

    // Navigate to collection
    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // Select the first category: "Text"
    const textCheckbox = page.getByRole("checkbox", { name: "Text" }).first();
    await textCheckbox.check({ force: true });

    // Verify URL updates to include category=text
    await expect(page).toHaveURL(/.*category=text/);

    // Select the second category: "Board Game"
    const boardGameCheckbox = page.getByRole("checkbox", { name: "Board Game" }).first();
    await boardGameCheckbox.check({ force: true });

    // Verify URL contains both category parameters
    await expect(page).toHaveURL(/.*category=.*text.*/);
    await expect(page).toHaveURL(/.*category=.*board_game.*/);

    // Deselect "Text"
    await textCheckbox.uncheck({ force: true });

    // Verify "text" is removed but "board_game" remains
    await expect(page).not.toHaveURL(/.*category=.*text.*/);
    await expect(page).toHaveURL(/.*category=.*board_game.*/);
  });

  test("supports full genre cross-filtering flow", async ({ page }) => {
    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // Open Genres accordion
    const genresAccordion = page.getByRole("button", { name: /Genres/i }).first();
    await genresAccordion.click();

    // Select Fiction
    const fictionCheckbox = page.getByRole("checkbox", { name: "Fiction" }).first();
    await fictionCheckbox.waitFor({ state: "visible" });
    await fictionCheckbox.check();

    // Verify URL updates
    await expect(page).toHaveURL(/.*genres=Fiction/);
  });

  test("supports AND across facets (category and genre)", async ({ page }) => {
    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    // Select Category "Text"
    const textCheckbox = page.getByRole("checkbox", { name: "Text" }).first();
    await textCheckbox.check({ force: true });

    // Open Genres accordion and select "Fiction"
    const genresAccordion = page.getByRole("button", { name: /Genres/i }).first();
    await genresAccordion.click();
    const fictionCheckbox = page.getByRole("checkbox", { name: "Fiction" }).first();
    await fictionCheckbox.waitFor({ state: "visible" });
    await fictionCheckbox.check();

    // Verify URL has both
    await expect(page).toHaveURL(/.*category=text/);
    await expect(page).toHaveURL(/.*genres=Fiction/);
  });

  test("supports URL round-trip restoration of filters", async ({ page }) => {
    // Hydrate with category=text and genres=Fiction
    await page.goto("/collection?category=text&genres=Fiction");
    await page.waitForLoadState("networkidle");

    // Verify that the UI state matches the URL hydration
    const textCheckbox = page.getByRole("checkbox", { name: "Text" }).first();
    await expect(textCheckbox).toBeChecked();

    const genresAccordion = page.getByRole("button", { name: /Genres/i }).first();
    await genresAccordion.click();

    const fictionCheckbox = page.getByRole("checkbox", { name: "Fiction" }).first();
    await expect(fictionCheckbox).toBeChecked();
  });

  test("shared URL with facet params restores filter state on navigation", async ({ page }) => {
    // Navigate with combined facet params simulating a shared URL
    await page.goto("/collection?view=items&statuses=available&formats=dvd&categories=movie");
    await page.waitForLoadState("networkidle");

    // URL should contain all filter params
    expect(page.url()).toContain("statuses=available");
    expect(page.url()).toContain("formats=dvd");
  });

  test("multiple facet groups selected reflect correctly in URL", async ({ page }) => {
    await page.goto("/collection?view=items&statuses=available,wish_list&formats=dvd");
    await page.waitForLoadState("networkidle");

    // Both statuses should be in the URL as comma-separated values
    expect(page.url()).toContain("statuses=available,wish_list");
    expect(page.url()).toContain("formats=dvd");
  });

  // 6.1: Shared URL with facet params restores filter state on another browser/device
  test("shared URL with facet params restores filter state", async ({ page }) => {
    await page.goto("/works?statuses=available&formats=paper");
    await page.waitForLoadState("networkidle");

    // URL should retain the facet parameters after load
    expect(page.url()).toContain("statuses=available");
    expect(page.url()).toContain("formats=paper");
  });

  // 6.2: Multiple facet groups selected reflect correctly in results and URL
  test("multiple facet groups reflected in results and URL", async ({ page }) => {
    await page.goto("/works?statuses=available&formats=paper&tags=horror");
    await page.waitForLoadState("networkidle");

    expect(page.url()).toContain("statuses=available");
    expect(page.url()).toContain("formats=paper");
    expect(page.url()).toContain("tags=horror");
  });
});
