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

test.describe("Snap Cover Workflow", () => {
  test("should display 503 error message when vision extraction fails", async ({ page }) => {
    // 1. Mock the API response (Asynchronous)
    await page.route("**/api/vision/extract", async route => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 202,
          json: { success: true, data: { task_id: "test-task-fail" } },
        });
      }
      return route.continue();
    });

    await page.route("**/api/vision/extract/test-task-fail", async route => {
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

    // Mock user authentication state
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

    // 2. Navigate to the scan page
    await page.goto("/scan");

    // 3. Switch to "Snap Cover" tab
    await page.click('button:has-text("Snap Cover")');

    // 4. Trigger file upload directly via the input element
    // This avoids issues with UI conditional rendering (Desktop vs Mobile buttons)
    await page.setInputFiles('input[type="file"]', {
      name: "test_cover.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-image-data"),
    });

    // 5. Assert that the error message is displayed after polling fails
    const errorText = page.getByText("Vision extraction failed. All fallback methods").first();
    await expect(errorText).toBeVisible();

    // 6. Verify that "Manual Item Entry" is automatically shown (Resilient Ingestion fallback)
    const manualEntryHeading = page.getByText("Manual Item Entry");
    await expect(manualEntryHeading).toBeVisible();
  });
});
