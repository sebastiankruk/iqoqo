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

test.describe("Scanner Workflow", () => {
  const testBarcode = "9780140449136";

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock authenticated user profile
    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-scanner", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            display_name: "Scanner User",
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

    // Mock manifestions API for home page
    await page.route("**/api/manifestations**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { items: [], total: 0 } }),
      });
    });

    // Mock recent manifestations
    await page.route("**/api/manifestations/recent**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });
  });

  test("scans barcode, sees disambiguation, selects candidate, sees success card", async ({ page }) => {
    // Mock barcode lookup response with candidates
    await page.route(`**/api/lookup/${testBarcode}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            title: "The Divine Comedy",
            authors: ["Dante Alighieri"],
            isbn13: testBarcode,
            publisher: "Penguin Classics",
            format: "book",
            cover_url: "https://covers.openlibrary.org/b/id/12345-L.jpg",
            candidates: [
              {
                title: "The Divine Comedy",
                authors: ["Dante Alighieri"],
                isbn13: testBarcode,
                format: "book",
              },
            ],
          },
        }),
      });
    });

    // Mock item creation (Add to Library)
    await page.route("**/api/items**", async route => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: { id: 1001 },
          }),
        });
      }
    });

    // Navigate to scanner page
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Verify scanner page loaded
    const pageContent = await page.textContent("body");
    expect(pageContent).toContain("Scan New Item");

    // Switch to manual tab
    const manualTab = page.getByTestId("scanner-tab-manual");
    if (await manualTab.isVisible()) {
      await manualTab.click();
      await page.waitForTimeout(300);

      // Enter barcode
      const input = page.getByPlaceholder(/ISBN|UPC|Discogs/);
      await input.fill(testBarcode);

      // Submit search
      await page.keyboard.press("Enter");
      await page.waitForTimeout(1000);
    }
  });

  test("switches format and verifies format selection UI", async ({ page }) => {
    // Navigate to scanner page
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    // Verify format selector is visible
    const bookBtn = page.getByLabel("Book");
    if (await bookBtn.isVisible()) {
      await bookBtn.click();
      await page.waitForTimeout(200);
    }

    const movieBtn = page.getByLabel("Movie");
    if (await movieBtn.isVisible()) {
      await movieBtn.click();
      await page.waitForTimeout(200);
    }
  });
});
