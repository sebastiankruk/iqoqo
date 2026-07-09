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
      manifestation: { id: 1000, title: "Test Book" },
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
    const bodyText = await page.innerText("body");
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

test.describe("v0.7.0 Token-Based Wishlist Sharing & Isolation", () => {
  const secretShareToken = "wishlist-token-xyz-7890";
  const targetSharedUrl = `/share/${secretShareToken}`;

  test("should render shared catalog elements in view-only mode for anonymous guests using a valid token", async ({
    page,
  }) => {
    // Navigate anonymously directly to the shared public wishlist endpoint
    await page.goto(targetSharedUrl);
    await page.waitForLoadState("networkidle");

    // Confirm that the wishlist owner's shared catalog elements are parsed and rendered properly
    const gridContainer = page.locator('[data-testid="collection-grid"]');
    await expect(gridContainer).toBeVisible();
    await expect(gridContainer.locator('[data-testid="item-card"]')).not.toHaveCount(0);

    // Assert strict view-only constraints on the layout to verify read-only boundaries
    const addContributionButton = page.locator('button:has-text("Add Item")');
    const deleteIconButton = page.locator('button[aria-label="Delete manifestation"]').first();
    const editMetadataButton = page.locator('button:has-text("Edit Metadata")').first();

    await expect(addContributionButton).not.toBeVisible();
    await expect(deleteIconButton).not.toBeVisible();
    await expect(editMetadataButton).not.toBeVisible();
  });

  test("should reject unauthorized actions and block directory traversing to restricted admin panels", async ({
    page,
  }) => {
    // Navigate anonymously
    await page.goto(targetSharedUrl);

    // 1. Verify that trying to force-navigate to internal panels triggers a security redirect
    await page.goto("/admin/settings");
    await expect(page).toHaveURL(/\/login/);

    // 2. Verify that trying to force-navigate to private profile settings does the same
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("FRBR Virtual Item Boundary", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the user profile to simulate an authenticated item owner
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "owner-user-id",
            email: "owner@iqoqo.local",
            permissions: ["update:item", "write:metadata", "upload:cover"],
            roles: [],
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

  test("should hide the QR Code button when viewing a virtual wishlist item (id < 0)", async ({ page }) => {
    // Mock the backend to return a virtual wishlist item payload.
    // Virtual items are UserWorkIntent adapters with negative IDs (id = -intent_id).
    // They have no physical copy on a shelf, so the QR Code button must be absent.
    await page.route("**/api/items/-10**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: -10,
            title: "Virtual Wishlist Book",
            status: "want_to_read",
            collection_status: "wish_list",
            manifestation_id: null,
            is_owner: true,
            owner_id: "owner-user-id",
            meta: { format: "book" },
          },
        }),
      });
    });

    // Mock the item logs endpoint — virtual items return an empty array
    await page.route("**/api/items/-10/logs**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.goto("/item/-10");
    await page.waitForLoadState("networkidle");

    // Assert the QR Code button is strictly absent for virtual items.
    // This is the FRBR boundary tripwire: virtual items have no physical copy to tag.
    const qrCodeButton = page.getByTestId("qrcode-btn");
    await expect(qrCodeButton).toHaveCount(0);

    // Also assert by text content
    const qrCodeButtonByText = page.locator("button", { hasText: "Print QR Code" });
    await expect(qrCodeButtonByText).toHaveCount(0);
  });
});
