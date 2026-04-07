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

test.describe("Jigsaw Puzzle Workflow", () => {
  test("should scan and add a jigsaw puzzle successfully", async ({ page }) => {
    // 1. Login
    await page.goto("/login");
    await page.fill('input[name="email"]', "test@iqoqo.org");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');

    // 2. Go to Scanner and Select Puzzle Mode
    await page.goto("/scan");
    await page.click('button:has-text("Puzzle")');

    // 3. Mock Barcode API Response (Simulating a successful scan)
    // In a real test environment, we'd use a mock service worker or
    // intercept the API call to /api/lookup/4005556199999
    await page.route("**/api/lookup/4005556199999*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            title: "Starry Night 1000pc",
            manufacturer: "Ravensburger",
            format: "puzzle",
            metadata: { piece_count: 1000, dimensions: "70x50cm" },
          },
          error: null,
        }),
      });
    });

    // 4. Trigger manual entry as a fallback for the scan
    await page.click("text=Enter Barcode Manually");
    await page.fill('input[placeholder="Enter barcode..."]', "4005556199999");
    await page.keyboard.press("Enter");

    // 5. Verify Item Card is created
    await expect(page.locator("text=Starry Night 1000pc")).toBeVisible();
    await expect(page.locator("text=1000 Pieces")).toBeVisible();

    // 6. Confirm addition
    await page.click('button:has-text("Add to Collection")');
    await expect(page).toHaveURL(/\/item\/.*/);
  });
});
