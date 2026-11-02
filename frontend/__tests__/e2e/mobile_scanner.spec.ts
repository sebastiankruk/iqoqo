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
/**
 * Playwright E2E mobile tests for continuous batch scanning, haptic feedback hooks,
 * and <= 3-click unified manual lookup on /scan (C98).
 */
import { test, expect } from "@playwright/test";

test.describe("Mobile Scanner & Batch Mode (C98)", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  const testIsbn = "9780451524935";

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock authenticated user session
    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-mobile-scanner", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "user-mobile-scanner-1",
            email: "mobile-scanner@iqoqo.local",
            display_name: "Mobile Scanner User",
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
          data: { federation_enabled: false, version: "1.0.0" },
        }),
      });
    });

    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route("**/api/stats/facets**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: {} }),
      });
    });

    await page.route("**/api/items**", async route => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: 888 } }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { items: [], total: 0 } }),
        });
      }
    });

    await page.route("**/api/manifestations/recent**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });
  });

  test("toggles continuous batch scan mode on /scan", async ({ page }) => {
    await page.goto("/scan");

    const batchButton = page.getByRole("button", { name: /batch mode/i });
    await expect(batchButton).toBeVisible();
    await expect(batchButton).toHaveAttribute("aria-pressed", "false");

    // Toggle on
    await batchButton.click();
    await expect(batchButton).toHaveAttribute("aria-pressed", "true");

    // Toggle off
    await batchButton.click();
    await expect(batchButton).toHaveAttribute("aria-pressed", "false");
  });

  test("continuous batch mode auto-adds scanned item and resets without redirect", async ({ page }) => {
    // Mock lookup response
    await page.route(`**/api/lookup/${testIsbn}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            title: "Nineteen Eighty-Four",
            authors: ["George Orwell"],
            isbn13: testIsbn,
            format: "book",
            manifestation_id: 42,
          },
        }),
      });
    });

    // Mock /scan ingestion
    let scanCalls = 0;
    await page.route("**/api/scan", async route => {
      if (route.request().method() === "POST") {
        scanCalls += 1;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              item_id: 101,
              manifestation_id: 42,
              action: "added_to_shelf",
            },
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/scan");

    // Activate Batch Mode
    const batchButton = page.getByRole("button", { name: /batch mode/i });
    await batchButton.click();
    await expect(batchButton).toHaveAttribute("aria-pressed", "true");

    // Enter barcode via unified lookup input
    const lookupInput = page.getByTestId("unified-lookup-input");
    await lookupInput.fill(testIsbn);
    await page.getByTestId("unified-lookup-submit").click();

    // Verify scan was ingested directly
    await expect.poll(() => scanCalls).toBe(1);

    // Toast notification confirms addition
    await expect(page.getByText(/added .* to collection/i)).toBeVisible();

    // Still on /scan without modal redirect
    expect(page.url()).toContain("/scan");
    await expect(page.getByTestId("unified-lookup-input")).toBeVisible();

    // Queue badge shows 1
    await expect(batchButton.getByText("1")).toBeVisible();
  });

  test("completes manual lookup in <= 3 clicks from dashboard", async ({ page }) => {
    await page.route(`**/api/lookup/${testIsbn}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            title: "Nineteen Eighty-Four",
            authors: ["George Orwell"],
            isbn13: testIsbn,
            format: "book",
            manifestation_id: 42,
          },
        }),
      });
    });

    await page.route("**/api/scan", async route => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              item_id: 202,
              manifestation_id: 42,
              action: "added_to_shelf",
            },
          }),
        });
      } else {
        await route.continue();
      }
    });

    // START ON DASHBOARD
    await page.goto("/");

    // CLICK 1: Navigate to scan page
    const scanNavLink = page.getByRole("link", { name: /^scan$/i }).first();
    await scanNavLink.click();
    await expect(page).toHaveURL(/\/scan/);

    // CLICK 2: Type ISBN into unified input and click Lookup/Search
    const lookupInput = page.getByTestId("unified-lookup-input");
    await expect(lookupInput).toBeVisible();
    await lookupInput.fill(testIsbn);
    await page.getByTestId("unified-lookup-submit").click();

    // SuccessCard opens with item details
    await expect(page.getByText("Nineteen Eighty-Four")).toBeVisible();

    // CLICK 3: Click Add to Shelf / Library
    const addButton = page.getByRole("button", { name: /add to shelf|add to library/i }).first();
    await expect(addButton).toBeVisible();
    await addButton.click();

    // Verified: Item added within 3 clicks
    await expect(page.getByText(/added to shelf|added.*library/i)).toBeVisible();
  });
});
