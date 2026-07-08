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
    // Intercept backend API call to mock the fallback resolution cascade
    const targetIsbn = "9788301000003";

    await page.route(`**/api/isbn/${targetIsbn}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          title: "Cascaded Book Title",
          barcode: targetIsbn,
          cover_url: "http://img.url/cover.jpg",
          description: "Recovered via downstream pipeline fallback",
          publisher: "Scientific Publishers",
          source: "Allegro Catalog",
        }),
      });
    });

    // Navigate to the scan workflow view
    await page.goto("/scan");

    // Open manual entry form modal within the scan view if viewfinder camera is default
    const manualEntryButton = page.locator('button:has-text("Manual Entry"), button:has-text("Wpisz ręcznie")');
    if (await manualEntryButton.isVisible()) {
      await manualEntryButton.click();
    }

    // Input the unindexed target ISBN code
    await page.fill('input[placeholder*="ISBN"], input[name="isbn"]', targetIsbn);
    await page.click('button[type="submit"]:has-text("Scan"), button[type="submit"]:has-text("Skanuj")');

    // Assert that the success card renders with the cascaded metadata fields
    const successCard = page.locator('[data-testid="success-card"]');
    await expect(successCard).toBeVisible({ timeout: 5000 });
    await expect(successCard).toContainText("Cascaded Book Title");

    // Verify source attribution is properly surfaced to the user for validation accountability
    await expect(successCard).toContainText("Allegro Catalog");

    // Confirm that the item can be added cleanly into the user library state
    await page.click('button:has-text("Add to Collection"), button:has-text("Dodaj do kolekcji")');
    await page.waitForURL("**/item/*");

    // Final verification on the item profile page view
    await expect(page.locator("h1")).toContainText("Cascaded Book Title");
  });
});
