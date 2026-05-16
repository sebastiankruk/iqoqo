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

test.describe("Infinite Scrolling Collection", () => {
  test("loads more items dynamically upon scrolling to the bottom of the grid", async ({ page }) => {
    const generateItems = (pageNum: number) =>
      Array.from({ length: 40 }).map((_, i) => ({
        id: pageNum * 100 + i,
        manifestation_id: pageNum * 100 + i,
        title: `Mock Infinite Item ${pageNum}-${i}`,
        authors: ["Test Author"],
        status: "want_to_read",
        collection_status: "available",
        meta: {},
      }));

    // Route profile so the page renders in logged-in (items) mode
    await page.route("**/api/profile/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ username: "testuser", permissions: [] }),
      });
    });

    // Route items API - serve page 1 or 2 based on query param
    await page.route("**/api/items**", async (route) => {
      const url = new URL(route.request().url());
      const pageParam = parseInt(url.searchParams.get("page") || "1", 10);

      if (pageParam === 1) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: generateItems(1),
            meta: { page: 1, pages: 2, total: 80 },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: generateItems(2),
            meta: { page: 2, pages: 2, total: 80 },
          }),
        });
      }
    });

    await page.goto("/collection");

    // Assert first page items rendered
    await expect(page.getByText("Mock Infinite Item 1-0")).toBeVisible();

    // Assert second page items NOT yet in DOM
    await expect(page.getByText("Mock Infinite Item 2-0")).toBeHidden();

    // Scroll to bottom to trigger IntersectionObserver
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Assert second page items now rendered via infinite scroll
    await expect(page.getByText("Mock Infinite Item 2-0")).toBeVisible();
  });
});
