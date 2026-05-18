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

test.describe("Complex Works & Series E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");

    try {
      const emailInput = page.getByLabel(/email/i);
      if (await emailInput.isVisible({ timeout: 2000 })) {
        await emailInput.fill("admin@iqoqo.local");
        await page.getByLabel(/password/i).fill("admin");
        await page.getByRole("button", { name: /sign in/i }).click();
        await page.waitForURL("**/dashboard*");
      }
    } catch {
      // Already logged in
    }
  });

  test("should display series parts in manifestation page", async ({ page }) => {
    // Intercept profile to grant metadata permissions
    await page.route("**/api/profile/**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { username: "admin", permissions: ["write:metadata", "read:metadata"] },
        }),
      });
    });

    // Intercept manifestation API returning a work_id
    await page.route("**/api/manifestations/100", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 100,
            expression_id: 10,
            work_id: 50,
            title: "The Fellowship of the Ring",
            isbn13: "9780007525546",
            publisher: "HarperCollins",
            year: 2012,
            cover_url: null,
            user_owns: false,
            meta: {},
          },
        }),
      });
    });

    // Intercept work parts endpoint returning the list of parts in sequence
    await page.route("**/api/works/50/parts", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            { part_work_id: 50, title: "The Fellowship of the Ring", sequence: 1 },
            { part_work_id: 51, title: "The Two Towers", sequence: 2 },
            { part_work_id: 52, title: "The Return of the King", sequence: 3 },
          ],
        }),
      });
    });

    await page.goto("/manifestation/100");

    // Verify visual components of series
    await expect(page.getByRole("heading", { name: "Series / Complex Work Parts" })).toBeVisible();
    await expect(page.getByText("The Fellowship of the Ring").first()).toBeVisible();
    await expect(page.getByText("The Two Towers").first()).toBeVisible();
    await expect(page.getByText("The Return of the King").first()).toBeVisible();
    await expect(page.getByText("Current Edition").first()).toBeVisible();
  });

  test("should display series parts in item details tab", async ({ page }) => {
    // Intercept profile
    await page.route("**/api/profile/**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { username: "admin", permissions: ["write:metadata", "read:metadata"] },
        }),
      });
    });

    // Intercept item detail returning parent work info
    await page.route("**/api/items/10", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 10,
            manifestation_id: 100,
            title: "The Fellowship of the Ring",
            status: "available",
            collection_status: "available",
            owner_name: "admin",
            owner_count: 1,
            manifestation_meta: {},
            work: { id: 50, title: "The Fellowship of the Ring" },
            expression: { id: 2 },
          },
        }),
      });
    });

    // Intercept work parts endpoint
    await page.route("**/api/works/50/parts", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            { part_work_id: 50, title: "The Fellowship of the Ring", sequence: 1 },
            { part_work_id: 51, title: "The Two Towers", sequence: 2 },
            { part_work_id: 52, title: "The Return of the King", sequence: 3 },
          ],
        }),
      });
    });

    await page.goto("/item/10");

    // Verify series list displays and highlights current
    await expect(page.getByRole("heading", { name: "Series / Complex Work Parts" })).toBeVisible();
    await expect(page.getByText("The Fellowship of the Ring").first()).toBeVisible();
    await expect(page.getByText("Current Item").first()).toBeVisible();
    await expect(page.getByText("The Two Towers").first()).toBeVisible();
  });
});
