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

test.describe("v0.7.15 UX Hotfixes", () => {
  test.beforeEach(async ({ page }) => {
    // Mock user authentication state
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "test-user-id",
            email: "test@example.com",
            display_name: "Test User",
            roles: ["user"],
            permissions: [],
          },
        },
      })
    );
    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false } },
      })
    );
  });

  test("Filter drawer ownership empty state defaults to showing all items", async ({ page }) => {
    // Mock manifestation endpoint
    await page.route("**/api/manifestations?*", route => {
      const url = new URL(route.request().url());
      const ownership = url.searchParams.get("ownership");

      // If ownership is empty, it means we show both owned and unowned
      return route.fulfill({
        status: 200,
        json: {
          success: true,
          data: [
            {
              id: 1,
              title: ownership ? `Manifestation (${ownership})` : "Manifestation (All)",
              format: "book",
            },
          ],
          pagination: { page: 1, per_page: 15, total: 1, pages: 1 },
        },
      });
    });

    await page.goto("/collection?view=manifestations");
    await page.waitForLoadState("networkidle");

    // By default, ownership should not be in the URL.
    expect(page.url()).not.toContain("ownership=");

    // Check if the item representing 'all' is visible
    await expect(page.getByText("Manifestation (All)").first()).toBeVisible();

    // Click "Owned" checkbox
    await page.getByRole("checkbox", { name: "Owned", exact: true }).check();
    await expect(page).toHaveURL(/ownership=owned/);
    await expect(page.getByText("Manifestation (owned)").first()).toBeVisible();

    // Uncheck "Owned", it should go back to default (both)
    await page.getByRole("checkbox", { name: "Owned", exact: true }).uncheck();
    await expect(page).not.toHaveURL(/ownership=owned/);
    await expect(page).not.toHaveURL(/ownership=not_owned/);
    await expect(page.getByText("Manifestation (All)").first()).toBeVisible();
  });

  test("Feedback form submission workflow", async ({ page }) => {
    // Mock initial empty feedback list
    let ticketCreated = false;

    await page.route("**/api/feedback?*", route => {
      if (!ticketCreated) {
        return route.fulfill({
          status: 200,
          json: { success: true, data: [], pagination: { total: 0 } },
        });
      } else {
        return route.fulfill({
          status: 200,
          json: {
            success: true,
            data: [
              {
                id: 1,
                feedback_type: "bug",
                status: "new",
                description: "This is a test bug report",
                user_display_name: "Test User",
                created_at: new Date().toISOString(),
              },
            ],
            pagination: { total: 1 },
          },
        });
      }
    });

    // Mock POST feedback
    await page.route("**/api/feedback", async route => {
      if (route.request().method() === "POST") {
        ticketCreated = true;
        return route.fulfill({
          status: 201,
          json: { success: true, data: { id: 1 } },
        });
      }
      return route.continue();
    });

    await page.goto("/feedback");
    await page.waitForLoadState("networkidle");

    // Click 'New Request' button
    await page
      .getByRole("button", { name: /New Request|Submit First Request/i })
      .first()
      .click();

    // Fill the form
    await page.locator("select").first().selectOption("bug");
    await page.getByPlaceholder(/Describe the issue or idea/i).fill("This is a test bug report");

    // Submit form
    await page.getByRole("button", { name: "Submit Feedback" }).click();

    // The modal should close and the new ticket should be in the list
    await expect(page.getByText("This is a test bug report")).toBeVisible({ timeout: 5000 });
  });

  test("dashboard toggles request personal and global aggregates", async ({ page }) => {
    await page.route("**/api/stats?scope=*", async route => {
      const scope = new URL(route.request().url()).searchParams.get("scope");
      const totalItems = scope === "global" ? 99 : 2;
      await route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            total_items: totalItems,
            items_reading: 1,
            to_read: 1,
            lent_items: 0,
            borrowed_items: 0,
          },
        },
      });
    });

    await page.goto("/");
    await expect(page.getByText("My Items")).toBeVisible();
    await expect(page.getByText("2").first()).toBeVisible();

    await page.getByRole("button", { name: /global/i }).click();
    await expect(page.getByText("All Items")).toBeVisible();
    await expect(page.getByText("99").first()).toBeVisible();

    await page.getByRole("button", { name: "Insights" }).click();
    await expect(page.getByRole("button", { name: "Insights" })).toHaveAttribute("aria-pressed", "true");
  });
});
