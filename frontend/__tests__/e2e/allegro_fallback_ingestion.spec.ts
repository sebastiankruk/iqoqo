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
// frontend/__tests__/e2e/allegro_fallback_ingestion.spec.ts
import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Phase 1 Ingestion Hardening - Allegro Strategy Cascade", () => {
  test.beforeEach(async ({ page }) => {
    // Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Login via direct Flask API call (avoids Next.js proxy POST body issues)
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = await loginRes.json();
    await page.goto(`/api/auth-exchange?token=${token}`);
    await page.waitForURL(/\/(collection)?$/);
  });

  test("should successfully ingest an item via Allegro fallback when standard ISBN search yields no results", async ({
    page,
  }) => {
    const targetIsbn = "9788301000003";

    // 1. Mock the lookup endpoint for the fallback book barcode (returns Allegro mock data)
    await page.route(`**/api/lookup/${targetIsbn}?format=book`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Cascaded Book Title",
            Format: "book",
            barcode: targetIsbn,
            Authors: ["Scientific Publishers"],
            meta: {
              publisher: "Scientific Publishers",
              source: "Allegro Catalog",
              description: "Recovered via downstream pipeline fallback",
            },
          },
        }),
      });
    });

    // 2. Mock the unified POST /scan endpoint
    await page.route("**/api/scan", async route => {
      const postData = route.request().postDataJSON();
      expect(postData.barcode).toBe(targetIsbn);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 1,
            manifestation_id: 100,
            barcode: targetIsbn,
            title: "Cascaded Book Title",
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
              title: "Cascaded Book Title",
              format: "book",
            },
          },
        }),
      });
    });

    // 4. Mock the config endpoint to match the version pattern in layout
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

    // Navigate to the scanner page
    await page.goto("/scan");

    // Switch to the Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // Enter target ISBN
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(targetIsbn);
    await barcodeInput.press("Enter");

    // Verify metadata displayed (title and author)
    await expect(page.getByText("Cascaded Book Title")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Scientific Publishers")).toBeVisible();

    // Click Add to Collection / Add to Library
    await page.getByRole("button", { name: "Add to Library" }).click();

    // Verify success message toast
    await expect(page.getByText(/"Cascaded Book Title" added to your library!/i)).toBeVisible();

    // Verify the application redirected to the newly created item
    await expect(page).toHaveURL(/.*\/item\/1/);
  });
});
