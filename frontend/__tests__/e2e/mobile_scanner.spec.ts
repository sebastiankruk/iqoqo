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
// frontend/__tests__/e2e/mobile_scanner.spec.ts

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Mobile Scanner Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Dismiss cookie consent
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock profile
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

    // Mock config
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

  test("should perform manual search lookup and add to library", async ({ page }) => {
    const testBarcode = "9780134685991";

    // Mock lookup
    await page.route(`**/api/lookup/${testBarcode}?format=book`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Manual Mobile Book",
            Format: "book",
            barcode: testBarcode,
            meta: {
              authors: ["Mobile Author"],
            },
            source: "Open Library",
          },
        }),
      });
    });

    // Mock scan API (add to library)
    await page.route("**/api/scan", async route => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 101,
            manifestation_id: 201,
            barcode: testBarcode,
            title: "Manual Mobile Book",
            message: "Successfully added to your collection",
          },
        }),
      });
    });

    // Mock target Item page redirect APIs
    await page.route("**/api/items/101**", async route => {
      const url = route.request().url();
      if (url.endsWith("/logs")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: [] }),
        });
      }
      if (url.includes("/loan-status")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: null }),
        });
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 101,
            owner_id: "test-user-id",
            status: "unread",
            collection_status: "available",
            title: "Manual Mobile Book",
            meta: { format: "book" },
            manifestation_meta: { format: "book" },
          },
        }),
      });
    });

    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Click Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // Input barcode & search
    const input = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await input.fill(testBarcode);
    await input.press("Enter");

    // Verify metadata shown
    await expect(page.getByText("Manual Mobile Book")).toBeVisible();

    // Add to library
    await page.getByRole("button", { name: "Add to Library" }).click();

    // Verify toast
    await expect(page.getByText(/"Manual Mobile Book" added to your library!/i)).toBeVisible();

    // Redirected
    await expect(page).toHaveURL(/.*\/item\?id=101/);
  });

  test("should perform snap cover vision extraction and auto-populate manual entry form", async ({ page }) => {
    // Mock the Vision task creation endpoint
    await page.route("**/api/vision/extract", async route => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 202,
          json: { success: true, data: { task_id: "test-task-success" } },
        });
      }
      return route.continue();
    });

    // Mock the Vision task polling endpoint
    await page.route("**/api/vision/extract/test-task-success", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          status: "completed",
          data: {
            Title: "Extracted Mobile Book",
            Format: "book",
            Authors: ["Author Extracted"],
            Publisher: "Vision House",
            Year: 2026,
          },
        }),
      });
    });

    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Click Snap Cover tab
    await page.click('button:has-text("Snap Cover")');

    // Trigger file upload
    await page.setInputFiles('input[type="file"]', {
      name: "test_cover_mobile.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-image-data"),
    });

    // Verify manual entry is populated with extracted details
    const titleInput = page.locator('input[placeholder="Title"]');
    const authorInput = page.locator('input[placeholder="Authors (comma-separated)"]');

    await expect(titleInput).toHaveValue("Extracted Mobile Book");
    await expect(authorInput).toHaveValue("Author Extracted");
  });
});
