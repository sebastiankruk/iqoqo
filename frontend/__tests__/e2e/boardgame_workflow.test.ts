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

test.describe("Board Game Ingestion Workflow", () => {
  test("should allow user to scan a board game barcode and add to collection", async ({ page }) => {
    // 0. Mock User Profile and Config
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
          data: { federation_enabled: false, version: "0.3.0" },
        }),
      });
    });

    // 1. Mock the lookup endpoint for board game barcode (BGG)
    const testBarcode = "681706704";
    await page.route(`**/api/lookup/${testBarcode}?format=boardgame`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Catan",
            Format: "game",
            barcode: testBarcode,
            meta: {
              min_players: 3,
              max_players: 4,
              mechanics: ["Dice Rolling", "Trading"],
              playing_time: 60,
              designers: ["Klaus Teuber"],
            },
          },
        }),
      });
    });

    // 2. Mock the unified POST /scan endpoint
    await page.route("**/api/scan", async route => {
      const postData = route.request().postDataJSON();
      expect(postData.barcode).toBe(testBarcode);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 2,
            manifestation_id: 200,
            barcode: testBarcode,
            title: "Catan",
            message: "Successfully added to your collection",
          },
        }),
      });
    });

    // 3. Mock the target Item page to prevent ECONNREFUSED on redirect
    await page.route("**/api/items/2**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 2,
            manifestation: {
              id: 200,
              title: "Catan",
              format: "game",
            },
          },
        }),
      });
    });

    // 4. Navigate to the scanner page
    await page.goto("/scan");

    // 5. Verify scanner page loads
    await expect(page.getByText("Tap to start camera")).toBeVisible();

    // 6. Select the Game format from the top pill menu
    await page.getByRole("button", { name: "Game" }).click();

    // 7. Switch to the Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 8. Enter barcode for a board game
    const barcodeInput = page.getByPlaceholder("Enter barcode or title...");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // 9. Verify BGG metadata displayed (title, players, mechanics)
    await expect(page.getByText("Catan")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("3-4 players")).toBeVisible();
    await expect(page.getByText("Dice Rolling")).toBeVisible();

    // 10. Click Add to Collection
    await page.getByRole("button", { name: "Add to Collection" }).click();

    // 11. Verify dynamic success message toast
    await expect(page.getByText(/"Catan" added to your library!/i)).toBeVisible();

    // 12. Verify the application redirected to the newly created item
    await expect(page).toHaveURL(/.*\/item\/2/);
  });

  test("should allow user to search board game by barcode", async ({ page }) => {
    // 0. Mock User Profile and Config
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
          data: { federation_enabled: false, version: "0.3.0" },
        }),
      });
    });

    // 1. Mock the lookup endpoint for board game barcode
    const testBarcode = "4005556199998";
    await page.route(`**/api/lookup/${testBarcode}?format=boardgame`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Carcassonne",
            Format: "game",
            barcode: testBarcode,
            meta: {
              min_players: 2,
              max_players: 5,
              mechanics: ["Tile Placement", "Drafting"],
              playing_time: 45,
            },
          },
        }),
      });
    });

    // 2. Mock the POST /scan endpoint
    await page.route("**/api/scan", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 3,
            manifestation_id: 300,
            title: "Carcassonne",
            message: "Successfully added to your collection",
          },
        }),
      });
    });

    // 3. Navigate to scanner page
    await page.goto("/scan");

    // 4. Select Game format
    await page.getByRole("button", { name: "Game" }).click();

    // 5. Switch to Manual Search
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 6. Enter board game barcode
    const searchInput = page.getByPlaceholder("Enter barcode or title...");
    await searchInput.fill(testBarcode);
    await searchInput.press("Enter");

    // 7. Verify metadata displayed
    await expect(page.getByText("Carcassonne")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("2-5 players")).toBeVisible();

    // 8. Add to collection
    await page.getByRole("button", { name: "Add to Collection" }).click();

    // 9. Verify success
    await expect(page.getByText(/"Carcassonne" added to your library!/i)).toBeVisible();
  });
});
