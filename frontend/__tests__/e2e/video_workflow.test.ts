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
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Video Media Ingestion Workflow", () => {
  test("should allow user to scan a DVD barcode and add to collection", async ({ page }) => {
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
          data: { federation_enabled: false, version: packageJson.version },
        }),
      });
    });

    // 1. Mock the lookup endpoint for DVD barcode (TMDB)
    const testBarcode = "883929153526";
    await page.route(`**/api/lookup/${testBarcode}?format=movie`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Inception",
            Format: "video",
            barcode: testBarcode,
            meta: {
              directors: ["Christopher Nolan"],
              cast: ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
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
            item_id: 1,
            manifestation_id: 100,
            barcode: testBarcode,
            title: "Inception",
            message: "Successfully added to your collection",
          },
        }),
      });
    });

    // 3. Mock the target Item page to prevent ECONNREFUSED on redirect
    await page.route("**/api/items/1**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 1,
            manifestation: {
              id: 100,
              title: "Inception",
              format: "video",
            },
          },
        }),
      });
    });

    // 4. Navigate to the scanner page
    await page.goto("/scan");

    // 5. Verify scanner page loads
    await expect(page.getByText("Tap to start camera")).toBeVisible();

    // 6. Select the Video format from the top pill menu
    await page.getByRole("button", { name: "Movie" }).click();

    // 7. Switch to the Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 8. Enter barcode for a DVD
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // 9. Verify TMDB metadata displayed (title and cast)
    await expect(page.getByText("Inception")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Christopher Nolan")).toBeVisible();
    await expect(page.getByText("Leonardo DiCaprio")).toBeVisible();

    // 10. Click Add to Collection
    await page.getByRole("button", { name: "Add to Library" }).click();

    // 11. Verify dynamic success message toast
    await expect(page.getByText(/"Inception" added to your library!/i)).toBeVisible();

    // 12. Verify the application redirected to the newly created item
    await expect(page).toHaveURL(/.*\/item\/1/);
  });
});
