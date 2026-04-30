// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Lending Workflow", () => {
  test("can search for a user and lend an item", async ({ page }) => {
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

    // 1. Mock the lookup endpoint for manual entry
    const testBarcode = "999999999999";
    await page.route(`**/api/lookup/${testBarcode}?format=book`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Lending Test Book",
            Format: "book",
            barcode: testBarcode,
            meta: {
              authors: ["Test Author"],
            },
            source: "Open Library",
          },
        }),
      });
    });

    // Mock user search
    await page.route("**/api/profile/users/search?q=Bob", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: "friend-id",
              email: "bob@example.com",
              display_name: "Bob Friend",
            },
          ],
        }),
      })
    );

    // 2. Navigate to Scanner page
    await page.goto("/scan");

    // 3. Switch to Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 4. Enter barcode
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // 5. Verify metadata displayed
    await expect(page.getByText("Lending Test Book")).toBeVisible({ timeout: 5000 });

    // 6. Click Add to Collection
    await page.getByRole("button", { name: "Add to My Collection" }).click();

    // 7. Verify dynamic success message toast
    await expect(page.getByText(/"Lending Test Book" added to your library!/i)).toBeVisible();

    // 8. The application redirects to the newly created item
    await expect(page).toHaveURL(/.*\/item\/\d+/);

    // 9. Wait for the page to load
    await expect(page.getByText("Availability & Condition")).toBeVisible();

    // 10. Select "Lent Out" from the collection status dropdown
    const collectionStatusSelect = page.locator('select[aria-label="Collection status"]');
    await collectionStatusSelect.selectOption("lent");

    // 11. Verify the dialog appears
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Lent Out Item")).toBeVisible();

    // 12. Type "Bob" into the borrower name input to trigger search
    const borrowerInput = page.getByPlaceholder("Search user or enter name...");
    await borrowerInput.fill("Bob");

    // 13. Wait for the search results to appear and click "Bob Friend"
    const searchResult = page.getByText("Bob Friend");
    await expect(searchResult).toBeVisible();
    await searchResult.click();

    // 14. Verify the input is populated with the selected user's name
    await expect(borrowerInput).toHaveValue("Bob Friend");

    // 15. Submit the dialog
    await page.getByRole("button", { name: "Confirm" }).click();

    // 16. Verify the success toast appears
    await expect(page.getByText(/Item marked as lent to Bob Friend/i)).toBeVisible();
  });
});
