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

test.describe("Feedback & Ticket Lifecycle (v0.7.15)", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // 2. Mock user profile
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "user-alpha",
            email: "alpha@iqoqo.local",
            display_name: "Alpha User",
            roles: ["admin"],
            permissions: ["tickets:admin", "tickets:creator"],
          },
        }),
      });
    });

    // 3. Mock config
    await page.route("**/api/config**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federation_enabled: false },
        }),
      });
    });
  });

  test("full ticket submission and detail interaction workflow", async ({ page }) => {
    const mockTickets = [
      {
        id: 1,
        user_id: "user-alpha",
        user_display_name: "Alpha User",
        user_email: "alpha@iqoqo.local",
        feedback_type: "feature_request",
        description: "Add keyboard navigation shortcuts for catalog inspection",
        status: "new",
        attachments: [],
        comments: [],
        comments_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    // Mock GET /api/feedback
    await page.route("**/api/feedback?*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockTickets,
          pagination: { page: 1, per_page: 15, total: mockTickets.length, pages: 1 },
        }),
      });
    });

    // Mock GET /api/feedback/1
    await page.route("**/api/feedback/1", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockTickets[0],
        }),
      });
    });

    // Navigate to /feedback
    await page.goto("/feedback");
    await page.waitForLoadState("networkidle");

    // 1. Verify Page Header and Admin View Indicator
    await expect(page.getByRole("heading", { name: "Help & Feedback" })).toBeVisible();
    await expect(page.getByText("Admin View Enabled")).toBeVisible();

    // 2. Verify Ticket Tile Rendering
    await expect(page.getByText("Add keyboard navigation shortcuts for catalog inspection")).toBeVisible();
    await expect(page.getByText("Feature Request")).toBeVisible();

    // 3. Filter by keyword
    const searchInput = page.getByPlaceholder("Filter by keyword...");
    await searchInput.fill("keyboard");
    await expect(page.getByText("Add keyboard navigation shortcuts for catalog inspection")).toBeVisible();

    await searchInput.fill("nonexistent keyword");
    await expect(page.getByText("No feedback tickets found")).toBeVisible();

    // 4. Reset Filters
    await page.getByRole("button", { name: "Reset" }).click();
    await expect(page.getByText("Add keyboard navigation shortcuts for catalog inspection")).toBeVisible();

    // 5. Open Ticket Detail Modal
    await page.getByText("Add keyboard navigation shortcuts for catalog inspection").click();
    const detailDialog = page.getByRole("dialog");
    await expect(detailDialog).toBeVisible();
    await expect(detailDialog.getByText("Ticket #1")).toBeVisible();
  });
});
