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

test.describe("LEGO Sets Workflow", () => {
  test("should lookup LEGO set 10318 and add to shelf", async ({ page }) => {
    // 0. Mock User Profile and Config
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "collector@iqoqo.local",
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

    // 1. Mock Lookup Response for set 10318
    await page.route("**/api/lookup/10318*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            title: "Concorde",
            set_number: "10318-1",
            year: 2023,
            piece_count: 2083,
            minifig_count: 0,
            theme: "Icons",
            format: "standard_set",
            category: "lego",
            data_source: "rebrickable",
          },
          error: null,
        }),
      });
    });

    // 2. Mock POST /api/scan endpoint
    await page.route("**/api/scan", async route => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 101,
            manifestation_id: 201,
            title: "Concorde",
            is_new_manifestation: true,
          },
        }),
      });
    });

    // 3. Go to Scan page
    await page.goto("/scan");

    // 4. Select LEGO Sets media filter in TopBar if present
    const legoBtn = page.getByRole("button", { name: /LEGO Sets|LEGO/i });
    if (await legoBtn.isVisible()) {
      await legoBtn.click();
    }

    // 5. Switch to Manual Search tab
    const manualSearchBtn = page.getByRole("button", { name: "Manual Search" });
    if (await manualSearchBtn.isVisible()) {
      await manualSearchBtn.click();
    }

    // 6. Fill in LEGO set number
    const searchInput = page
      .locator('input[placeholder*="ISBN, UPC"], input[type="search"], input[type="text"]')
      .first();
    await searchInput.fill("10318");
    await page.keyboard.press("Enter");

    // 7. Success card appears with set title
    await expect(page.locator("text=Concorde").first()).toBeVisible({ timeout: 10000 });

    // 8. Add to Shelf / Library
    const addBtn = page.getByRole("button", { name: /Add to (Shelf|Library)/i });
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await expect(page).toHaveURL(/\/item\/.*/);
    }
  });
});
