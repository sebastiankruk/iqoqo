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

test.describe("Wishlist Media Disambiguation (Vinyl, Audio, Games)", () => {
  test.beforeEach(async ({ page }) => {
    // Mock user profile & config
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
            permissions: ["upload:cover", "update:item", "write:metadata", "read:item"],
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

    await page.route("**/api/collections**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
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
            items: 1,
            items_wish_list: 1,
            items_available: 0,
            works: 1,
          },
        }),
      });
    });
  });

  test("catalogs a Vinyl to the Wishlist and verifies turntable/disc icon and audio aspect ratio in grid", async ({
    page,
  }) => {
    const testBarcode = "0602567973549";

    // 1. Mock lookup for Vinyl record
    await page.route(`**/api/lookup/${testBarcode}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Abbey Road",
            Format: "vinyl",
            work_type: "AudioWork",
            medium_type: "Vinyl",
            barcode: testBarcode,
            Authors: ["The Beatles"],
          },
        }),
      });
    });

    // 2. Mock POST /api/scan with wish_list collection status
    await page.route("**/api/scan", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: null,
            intent_id: 101,
            manifestation_id: 501,
            title: "Abbey Road",
            message: "Successfully added to your wishlist",
          },
        }),
      });
    });

    // 3. Mock GET /api/items to return the virtual wishlist item for Vinyl
    await page.route("**/api/items*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              is_virtual: true,
              id: -101,
              owner_id: "test-user-id",
              status: "want_to_listen",
              collection_status: "wish_list",
              title: "Abbey Road",
              authors: ["The Beatles"],
              content_type: "music",
              work_type: "AudioWork",
              medium_type: "Vinyl",
              cover_url: null,
              cover_status: null,
              is_owner: true,
              is_borrowed: false,
              is_hidden: false,
              tags: [],
            },
          ],
          meta: { page: 1, limit: 50, total: 1, pages: 1 },
          pagination: { total: 1, limit: 50, offset: 0, has_more: false },
        }),
      });
    });

    // 4. Navigate to scanner and add to wishlist
    await page.goto("/scan");
    await page.getByRole("button", { name: "Manual Search" }).click();
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // Click Add to Wishlist
    await page.getByRole("button", { name: "Add to Wishlist" }).click();
    await expect(page.getByText("Successfully added to your wishlist")).toBeVisible();

    // 5. Navigate to collection wishlist view
    await page.goto("/collection?statuses=wish_list");
    await page.waitForLoadState("networkidle");

    // 6. Verify Vinyl item card rendered in collection grid
    const itemCard = page.locator('[data-testid="item-card"]');
    await expect(itemCard).toBeVisible();
    await expect(itemCard.locator('[data-testid="card-title"]')).toHaveText("Abbey Road");
    await expect(itemCard).toContainText("The Beatles");

    // 7. Verify turntable / audio disc icon is displayed for the vinyl placeholder
    const discIcon = itemCard.locator("svg.lucide-disc");
    await expect(discIcon).toBeVisible();

    // 8. Verify square aspect ratio for audio media
    const coverContainer = itemCard.locator(".aspect-square");
    await expect(coverContainer).toBeVisible();
  });
});
