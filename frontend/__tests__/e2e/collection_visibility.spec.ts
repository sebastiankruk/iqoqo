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

test.describe("Collection Visibility Filtering and Bulk Update (C128)", () => {
  test("filters collection by visibility and bulk-updates selected items", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "vis-user",
            email: "vis@iqoqo.local",
            permissions: ["write:item", "update:item"],
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
          data: { federation_enabled: false, version: "1.1.0" },
        }),
      });
    });

    let lastPatchBody: Record<string, unknown> | null = null;
    await page.route("**/api/items/bulk-visibility", async route => {
      lastPatchBody = JSON.parse(route.request().postData() || "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { updated_count: 1, visibility: lastPatchBody?.visibility, item_ids: [101] },
        }),
      });
    });

    await page.route("**/api/items**", async route => {
      if (route.request().url().includes("bulk-visibility")) return;
      const url = route.request().url();
      const items = url.includes("visibility=friends_only")
        ? [
            {
              id: 102,
              manifestation_id: 202,
              owner_id: "vis-user",
              is_owner: true,
              status: "unread",
              collection_status: "available",
              visibility: "friends_only",
              is_hidden: true,
              title: "Friends Only Copy",
              authors: ["Author B"],
              meta: {},
            },
          ]
        : [
            {
              id: 101,
              manifestation_id: 201,
              owner_id: "vis-user",
              is_owner: true,
              status: "unread",
              collection_status: "available",
              visibility: "public",
              is_hidden: false,
              title: "Public Copy",
              authors: ["Author A"],
              meta: {},
            },
          ];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: items,
          meta: { page: 1, limit: 20, total: items.length, pages: 1 },
        }),
      });
    });

    await page.goto("/collection");
    await expect(page.locator('[data-testid="card-title"]', { hasText: "Public Copy" })).toBeVisible();

    const friendsCheckbox = page.locator('input[name="visibility_filter"]').nth(1);
    await friendsCheckbox.check();
    await expect(page).toHaveURL(/visibility=friends_only/);
    await expect(page.locator('[data-testid="card-title"]', { hasText: "Friends Only Copy" })).toBeVisible();

    await page.getByRole("button", { name: "Select" }).first().click();
    await expect(page.getByTestId("bulk-item-visibility-toolbar")).toBeVisible();
    await page.getByTestId("bulk-visibility-trigger").click();
    await page.getByTestId("bulk-visibility-menu").getByRole("menuitem").first().click();
    await expect.poll(() => lastPatchBody).toEqual({ item_ids: [102], visibility: "public" });
  });
});
