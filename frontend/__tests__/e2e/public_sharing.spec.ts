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
    await page.goto("/u/testuser");
    const input = page.getByPlaceholder(/Search by Title, ISBN, or UPC/i);
    await input.fill("1111111111111");

    // Wait for the search API response
    const responsePromise = page.waitForResponse(
      r => r.url().includes("/public/u/testuser/check") && r.status() === 200
    );
    await page.getByRole("button", { name: "Check if I have it" }).first().click();
    await responsePromise;

    // Wait for the search result card to appear (be specific to avoid matching toasts)
    const resultCard = page.locator("div[data-slot='card'].animate-in");
    await expect(resultCard).toBeVisible();

    // Check if the item title appears WITHIN the result card
    await expect(resultCard.getByText("Public Treasure").first()).toBeVisible();
    // Then check for the success label container WITHIN the result card
    await expect(resultCard.locator("p.text-primary.uppercase").first()).toBeVisible();
  });
});
