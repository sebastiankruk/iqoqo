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
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Jigsaw Puzzle Workflow", () => {
  test("should scan and add a jigsaw puzzle successfully", async ({ page }) => {
    // 0. Mock User Profile and Config (following existing pattern)
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            permissions: ["upload:cover", "update:item", "write:metadata"],
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
          data: { federation_enabled: false, version: packageJson.version },
        }),
      });
    });

    // 1. Go to Scanner (already authenticated via mocks)
    await page.goto("/scan");

    // 2. Select Puzzle Mode using accessible button
    await page.getByRole("button", { name: "Puzzle", exact: true }).click();

    // 3. Mock Barcode API Response (Simulating a successful scan)
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

    // 4. Mock the POST /scan endpoint for adding to collection
    await page.route("**/api/scan", async route => {
      const postData = route.request().postDataJSON();
      expect(postData.barcode).toBe("4005556199999");

      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 5,
            manifestation_id: 10,
            title: "Starry Night 1000pc",
            is_new_manifestation: true,
          },
        }),
      });
    });

    // 4. Switch to Manual Search tab to access the input
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 5. Fill in the barcode
    await page.fill('input[placeholder="ISBN, UPC, Discogs ID, or Artist – Title…"]', "4005556199999");
    await page.keyboard.press("Enter");

    // 6. Verify Item Card is created (title is visible in success card)
    await expect(page.locator("text=Starry Night 1000pc")).toBeVisible();

    // 7. Confirm addition
    await page.click('button:has-text("Add to Library")');
    await expect(page).toHaveURL(/\/item\/.*/);
  });
});
