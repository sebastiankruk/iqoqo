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

test.describe("Snap Cover Workflow", () => {
  test("should display 503 error message when vision extraction fails", async ({ page }) => {
    // 1. Mock the API response to return 503
    await page.route("**/api/vision/extract", async route => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          success: false,
          data: null,
          error:
            "Vision extraction failed. All fallback methods (Gemini, Ollama, Tesseract) were either unconfigured or failed. Please check the server logs.",
        }),
      });
    });

    // 2. Navigate to the scan page (mocking auth if necessary, assuming dev mode/bypass)
    // We might need to set a JWT token in localStorage if the page requires it
    await page.goto("/scan");

    // 3. Switch to "Snap Cover" tab
    await page.click('button:has-text("Snap Cover")');

    // 4. Click "Start Live Camera"
    // (Playwright will automatically wait until the element is attached after the tab switch)
    await page.click('button:has-text("Start Live Camera")');

    // 5. Click "Snap Live Frame"
    await page.click('button:has-text("Snap Live Frame")');

    // 6. Verify "Analyzing frame..." loading state (optional but good)
    // await expect(page.locator('text=Analyzing frame...')).toBeVisible();

    // 7. Assert that the error message is displayed
    const errorText = page.locator("text=Vision extraction failed. All fallback methods");
    await expect(errorText).toBeVisible();
    await expect(errorText).toHaveClass(/text-destructive/);

    // 8. Verify that "Manual Entry Form" is still accessible by switching to manual tab
    await page.click('button:has-text("Manual Search")');
    const manualEntryButton = page.locator('button:has-text("Manual Entry Form")');
    await expect(manualEntryButton).toBeVisible();
  });
});
