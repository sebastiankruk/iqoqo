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

test.describe("Public Sharing", () => {
  test("visitor can view public profile", async ({ page }) => {
    // This assumes a user 'testuser' exists and is public
    await page.goto("/u/testuser");
    await expect(page.locator("h1")).toContainText("Test User");
    await expect(page.getByText(/Public Items/i)).toBeVisible();
  });

  test("visitor sees empty state for empty collection", async ({ page }) => {
    await page.goto("/u/emptyuser");
    await expect(page.getByText(/Nothing here yet/i)).toBeVisible();
  });

  test("check inventory tool works", async ({ page }) => {
    // 1. Mock the inventory check API before navigating
    await page.route("**/public/u/testuser/check", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              type: "item",
              id: 3,
              manifestation_id: 10,
              title: "Public Treasure",
              cover_url: null,
              status: "on_shelf",
            },
          ],
        }),
      })
    );

    // 2. Navigate and wait for loading state
    await page.goto("/u/testuser");
    await page.waitForLoadState("networkidle");

    // 3. Fill the input
    const input = page.getByPlaceholder(/Search by Title, ISBN, or UPC/i);
    await input.fill("1111111111111");

    // 4. Submit form by pressing Enter to avoid React state hydration lag on button click
    await Promise.all([
      page.waitForResponse(r => r.url().includes("/public/u/testuser/check") && r.status() === 200, { timeout: 15000 }),
      input.press("Enter"),
    ]);

    // 5. Wait for the search result card to appear
    const resultCard = page.locator("#inventory-result-card");
    await expect(resultCard).toBeVisible();

    // Check if the item title appears WITHIN the result card (use fuzzy match)
    await expect(resultCard.getByText(/Treasure/i).first()).toBeVisible();
    // Then check for the success label container WITHIN the result card
    await expect(resultCard.locator("p.text-primary.uppercase").first()).toBeVisible();
  });
});
