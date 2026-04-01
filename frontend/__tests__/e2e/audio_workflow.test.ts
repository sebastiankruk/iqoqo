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

test.describe("Audio Media Workflow", () => {
  test("should display tracklist and support status updates for audio CD", async ({ page }) => {
    // 0. Mock User Profile and Config
    await page.route("**/api/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            permissions: ["upload:cover", "edit:item"]
          }
        })
      });
    });

    await page.route("**/api/config**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federation_enabled: false, version: "0.2.0" }
        })
      });
    });

    // 1. Mock the Item API response
    await page.route("**/api/items/1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 1,
            manifestation_id: 102,
            status: "available",
            title: "Kind of Blue",
            authors: ["Miles Davis"],
            manifestation_meta: {
              format: "CD",
              label: "Columbia",
              catalog_number: "CK 64935",
              matrix_number: "DIDP-070123",
              disc_count: 1,
              track_list: [
                { position: "1", title: "So What", duration_seconds: 562 },
                { position: "2", title: "Freddie Freeloader", duration_seconds: 586 },
              ],
            },
            work: {
              id: 50,
              title: "Kind of Blue",
              authors: ["Miles Davis"],
            },
            expression: {
              id: 75,
              content_type: "sound",
              language: "en",
            },
          },
        }),
      });
    });

    // 2. Mock Manifestation Polling (used by ItemDetail)
    await page.route("**/api/manifestations/102", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 102,
            title: "Kind of Blue",
            authors: ["Miles Davis"],
            meta: {
              format: "CD",
              label: "Columbia",
              catalog_number: "CK 64935",
              track_list: [
                { position: "1", title: "So What", duration_seconds: 562 },
                { position: "2", title: "Freddie Freeloader", duration_seconds: 586 },
              ],
            },
          },
        }),
      });
    });

    // 3. Navigate to the item page
    await page.goto("/item/1");

    // 4. Verify Audio Metadata rendering in ExtendedMetadata (usually in a tab or below header)
    // Based on ItemTabs default, it might be in the "Details" tab. 
    // We assume it's visible or we click the tab if needed.
    await expect(page.getByText("Release Information")).toBeVisible();
    await expect(page.getByText("Label")).toBeVisible();
    await expect(page.getByText("Columbia")).toBeVisible();
    await expect(page.getByText("Catalog #")).toBeVisible();

    // 5. Verify Tracklist rendering
    await expect(page.getByText("Tracklist")).toBeVisible();
    await expect(page.getByText("So What")).toBeVisible();
    await expect(page.getByText("9:22")).toBeVisible(); // 562s = 9m 22s

    // 6. Verify Categorized Status Dropdown in Sidebar
    const statusSelect = page.locator('select[aria-label="Item status"]');
    await expect(statusSelect).toBeVisible();
    
    // Check for optgroup labels
    const listeningGroup = page.locator('optgroup[label="Listening Progress"]');
    await expect(listeningGroup).toBeAttached();
    
    // 7. Update status to "Listening"
    await page.route("**/api/items/1", async (route) => {
      if (route.request().method() === "PATCH" || route.request().method() === "PUT") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });
    
    await statusSelect.selectOption("listening");
    await expect(page.getByText(/status updated/i)).toBeVisible();

    // 8. Verify Multi-Image Uploader UI
    // The section might take a moment to appear as profile loads
    const uploaderSection = page.getByText("Additional Scans");
    await expect(uploaderSection).toBeVisible({ timeout: 10000 });
    
    const labelSelect = page.locator("select").filter({ hasText: "Disc / Vinyl" });
    await expect(labelSelect).toBeVisible();
    
    await expect(page.getByText(/Upload [a-z]+ image/i)).toBeVisible();
  });
});
