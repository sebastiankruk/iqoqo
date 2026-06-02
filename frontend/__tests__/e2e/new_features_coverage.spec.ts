// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("New Features Coverage", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // 2. Mock user profile
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

    // 3. Mock config
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

    // 4. Mock taxonomies to prevent 401
    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            genres: [],
            publishers: [],
            tags: [],
            collections: [],
          },
        }),
      });
    });

    // 5. Mock stats to prevent 401
    await page.route("**/api/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            works: 1,
            expressions: 1,
            manifestations: 1,
            items: 1,
            to_read: 1,
            items_wish_list: 1,
          },
        }),
      });
    });
  });

  test("should support QR code generation, timeline history, and comments/ratings", async ({ page }) => {
    const itemId = 12345;

    // Mock GET /api/items/12345
    await page.route(`**/api/items/${itemId}**`, async route => {
      if (route.request().method() === "PUT") {
        const update = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: itemId, ...update } }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: itemId,
              title: "The Caveman Saga",
              status: "unread",
              collection_status: "available",
              is_owner: true,
              manifestation_id: 54321,
              meta: { format: "book" },
              manifestation_meta: { format: "book" },
              work: {
                id: 111,
                title: "The Caveman Saga",
                authors: ["Grog Elder"],
              },
              expression: {
                id: 222,
                content_type: "text",
                language: "eng",
              },
            },
          }),
        });
      }
    });

    // Mock GET /api/qrcode/12345
    await page.route(`**/api/qrcode/${itemId}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: Buffer.from("fake-png-content"),
      });
    });

    // Mock GET /api/items/12345/logs
    await page.route(`**/api/items/${itemId}/logs`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              old_status: null,
              new_status: "unread",
              changed_at: "2026-05-25T08:00:00Z",
              log_type: "creation",
              operator_name: "You",
              category: "text",
            },
            {
              old_status: "unread",
              new_status: "reading",
              changed_at: "2026-05-25T08:30:00Z",
              log_type: "progress",
              operator_name: "You",
              category: "text",
            },
          ],
        }),
      });
    });

    // Mock GET/POST for feedback
    const submittedFeedbacks: Array<{ rating: number; comment?: string }> = [];
    await page.route(`**/api/feedback/**`, async route => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        submittedFeedbacks.push(body);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: body }),
        });
      } else {
        // Return dummy feedbacks wrapped in data envelope
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              feedbacks: [
                {
                  id: 99,
                  user_id: "another-user-id",
                  operator_name: "Caveman Friend",
                  rating: 4,
                  comment: "Grog story good",
                  created_at: "2026-05-25T09:00:00Z",
                },
                ...submittedFeedbacks.map((f, index) => ({
                  id: 100 + index,
                  user_id: "test-user-id",
                  operator_name: "You",
                  rating: f.rating,
                  comment: f.comment,
                  created_at: "2026-05-25T09:30:00Z",
                })),
              ],
              stats: {
                average_rating: 4.0,
                total_ratings: 1 + submittedFeedbacks.length,
                rating_counts: { "1": 0, "2": 0, "3": 0, "4": 1, "5": submittedFeedbacks.length },
              },
            },
          }),
        });
      }
    });

    // 1. Navigate to Item Detail Page
    await page.goto(`/item?id=${itemId}`);
    await page.waitForLoadState("networkidle");

    // 2. Test QR Code Dialog
    await page.getByRole("button", { name: "Print QR Code" }).click();
    const qrDialog = page.getByRole("dialog");
    await expect(qrDialog).toBeVisible();
    await expect(qrDialog.getByText("Physical Copy Tracking Label")).toBeVisible();
    await expect(qrDialog.getByText("The Caveman Saga")).toBeVisible();
    // Close QR Code dialog
    await page.keyboard.press("Escape");
    await expect(qrDialog).not.toBeVisible();

    // 3. Test Timeline Log (History tab)
    await page.getByRole("button", { name: "History" }).click();
    const timelineLog = page.locator('[data-testid="frbr-timeline-log"]');
    await expect(timelineLog.getByText("Added to Collection")).toBeVisible();
    await expect(timelineLog.getByText("Progress Updated")).toBeVisible();
    await expect(timelineLog.getByText("by You").first()).toBeVisible();

    // 4. Test Comments and Ratings (Reviews tab)
    await page.getByRole("button", { name: "Reviews" }).click();

    // Toggle "Conceptual Work" tab and expect review text
    await expect(page.getByText("Grog story good")).toBeVisible();

    // Toggle other subtabs to verify level selection doesn't crash
    await page.getByRole("button", { name: "Expression" }).click();
    await page.getByRole("button", { name: "Edition" }).click();
    await page.getByRole("button", { name: "Personal Copy" }).click();
  });

  test("should display virtual want_to_read intents in the collection", async ({ page }) => {
    // Mock GET /api/items to return a synthesized virtual item
    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: -101, // Negative synthesized ID
              title: "Wanted Ancient Tale",
              status: "want_to_read",
              collection_status: "wish_list",
              is_owner: true,
              is_virtual: true,
              manifestation_id: 77777,
              meta: { format: "book" },
              manifestation_meta: { format: "book" },
              work: {
                id: 999,
                title: "Wanted Ancient Tale",
                authors: ["Stone Scholar"],
              },
            },
          ],
        }),
      });
    });

    // Navigate to Collection
    await page.goto("/collection?view=items");
    await page.waitForLoadState("networkidle");

    // Assert virtual item is shown
    await expect(page.getByText("Wanted Ancient Tale").first()).toBeVisible();
    await expect(page.locator('span[title="On Wish List"]').first()).toBeVisible();
  });
});
