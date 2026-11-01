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
 * E2E tests for mobile 4-action bottom navigation and zero-URL-rewrite catalog routing (C95).
 * Tests both Pixel 7 (412x915) and iPhone 14 (390x844) viewports.
 */
import { test, expect } from "@playwright/test";

const viewports = [
  { name: "Pixel 7", width: 412, height: 915 },
  { name: "iPhone 14", width: 390, height: 844 },
];

for (const vp of viewports) {
  test.describe(`Mobile Catalog Navigation (${vp.name})`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test.beforeEach(async ({ page }) => {
      await page
        .context()
        .addCookies([{ name: "iqoqo_session", value: "mock-session-c95", domain: "localhost", path: "/" }]);

      await page.route("**/api/profile**", async route => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: "mobile-nav-user",
              email: "mobilenav@iqoqo.local",
              display_name: "Mobile Collector",
              permissions: ["read:item", "write:item"],
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
            data: {
              federation_enabled: false,
              version: "1.0.0",
              maintenance_mode: false,
            },
          }),
        });
      });

      await page.route("**/api/items**", async route => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              items: [],
              total: 0,
            },
          }),
        });
      });

      await page.route("**/api/escalations/mine**", async route => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: [],
          }),
        });
      });
    });

    test("renders 4-action mobile bottom bar without login tab and navigates cleanly", async ({ page }) => {
      await page.goto("/");

      const bottomBar = page.locator(".fixed.bottom-0");
      await expect(bottomBar).toBeVisible();

      // Check all 4 primary action links exist
      const homeLink = bottomBar.locator('a[href="/"]');
      const scanLink = bottomBar.locator('a[href="/scan"]');
      const collectionLink = bottomBar.locator('a[href="/collection"]');
      const searchLink = bottomBar.locator('a[href="/collection?focus=search"]');

      await expect(homeLink).toBeVisible();
      await expect(scanLink).toBeVisible();
      await expect(collectionLink).toBeVisible();
      await expect(searchLink).toBeVisible();

      // Ensure no login link exists in the bottom bar
      const loginLink = bottomBar.locator('a[href="/login"]');
      await expect(loginLink).toHaveCount(0);

      // Tap Collection tab
      await collectionLink.click();
      await expect(page).toHaveURL(/\/collection/);

      // Tap Search tab
      await searchLink.click();
      await expect(page).toHaveURL(/\/collection\?focus=search/);
    });
  });
}
