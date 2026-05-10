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

test.describe("Wishlist and Progress Workflow", () => {
  test.beforeEach(async ({ page }) => {
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
  });

  test("should allow user to add an item to wishlist from scanner success card", async ({ page }) => {
    const testBarcode = "9780140449136";

    // 1. Mock lookup
    await page.route(`**/api/lookup/${testBarcode}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "The Odyssey",
            Format: "book",
            barcode: testBarcode,
            Authors: ["Homer"],
          },
        }),
      });
    });

    // 2. Intercept and mock POST /scan
    let capturedPayload: Record<string, unknown> | null = null;
    await page.route("**/api/scan", async route => {
      capturedPayload = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 42,
            manifestation_id: 420,
            title: "The Odyssey",
            message: "Successfully added to your wishlist",
          },
        }),
      });
    });

    // 3. Navigate and perform action
    await page.goto("/scan");
    await page.getByRole("button", { name: "Manual Search" }).click();
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // 4. Click Add to Wishlist
    await page.getByRole("button", { name: "Add to Wishlist" }).click();

    // 5. Verify payload and success message
    await expect(page.getByText(/"The Odyssey" added to your wishlist!/i)).toBeVisible();
    expect(capturedPayload).toMatchObject({ collection_status: "wish_list" });
  });

  test("should allow user to update progress and collection status via item sidebar", async ({ page }) => {
    const itemId = 999;
    
    // 1 & 2. Mock GET and PUT item
    const capturedUpdates: Record<string, unknown>[] = [];
    let currentItemState = {
      id: itemId,
      title: "Test Book",
      status: "unread",
      collection_status: "available",
      is_owner: true,
      manifestation_id: 1000,
      meta: { format: "book" },
      manifestation: { id: 1000, title: "Test Book" }
    };
    await page.route(`**/api/items/${itemId}**`, async route => {
      if (route.request().method() === "PUT") {
        const update = route.request().postDataJSON();
        capturedUpdates.push(update);
        currentItemState = { ...currentItemState, ...update };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: itemId } }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: currentItemState,
          }),
        });
      }
    });


    // 3. Navigate to item page
    page.on("console", msg => console.log("PAGE LOG:", msg.text()));
    page.on("pageerror", err => console.log("PAGE ERROR:", err.message));
    page.on("response", res => {
      if (res.status() === 404) console.log("404 URL:", res.url());
    });
    await page.goto(`/item/${itemId}`);
    await page.waitForLoadState("networkidle");
    const bodyText = await page.innerText('body');
    console.log("BODY TEXT:", bodyText.slice(0, 200));

    // 4. Update Progress Status to "Want to Read"
    const progressSelect = page.locator('select[aria-label="Item status"]');
    await progressSelect.waitFor({ state: "visible", timeout: 10000 });
    await progressSelect.selectOption("want_to_read");
    await expect(page.getByText(/Progress status updated to Want to Read/i)).toBeVisible();

    // 5. Update Collection Status to "On Wish List"
    const collectionSelect = page.locator('select[aria-label="Collection status"]');
    await collectionSelect.waitFor({ state: "visible" });
    await collectionSelect.selectOption("wish_list");
    await expect(page.getByText(/Collection status updated to On Wish List/i)).toBeVisible();

    // 6. Verify captured payloads
    expect(capturedUpdates).toContainEqual(expect.objectContaining({ status: "want_to_read" }));
    expect(capturedUpdates).toContainEqual(expect.objectContaining({ collection_status: "wish_list" }));
    
    // Allow a small window for re-render after toasts
    await page.waitForTimeout(1000);

    // 7. Verify status badges (case insensitive as they might be CSS transformed)
    await expect(page.locator("span.rounded-full", { hasText: /WANT TO READ/i })).toBeVisible({ timeout: 10000 });
    await expect(page.locator("span.rounded-full", { hasText: /ON WISH LIST/i })).toBeVisible({ timeout: 10000 });
  });
});
