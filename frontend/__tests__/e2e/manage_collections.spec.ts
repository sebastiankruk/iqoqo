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

test.describe("Manage Collections Modal Workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "e2e-user-id",
            email: "e2e@iqoqo.local",
            permissions: ["write:item"],
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
          data: { federation_enabled: false, version: "1.0.0" },
        }),
      });
    });

    // Mock existing collections — stateful to reflect CRUD mutations
    const mockCollections = [
      { id: 1, name: "Fantasy", parent_id: null },
      { id: 2, name: "Sci-Fi", parent_id: null },
    ];
    let nextId = 3;

    await page.route("**/api/collections**", async route => {
      const url = new URL(route.request().url());
      const idMatch = url.pathname.match(/\/collections\/(\d+)$/);
      const colId = idMatch ? parseInt(idMatch[1]) : null;

      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, collections: mockCollections }),
        });
      } else if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        const newCol = { id: nextId++, name: body.name, parent_id: null };
        mockCollections.push(newCol);
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({ success: true, collection: newCol }),
        });
      } else if (route.request().method() === "PUT" && colId) {
        const body = route.request().postDataJSON();
        const idx = mockCollections.findIndex(c => c.id === colId);
        if (idx >= 0) mockCollections[idx] = { ...mockCollections[idx], ...body };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      } else if (route.request().method() === "DELETE" && colId) {
        const idx = mockCollections.findIndex(c => c.id === colId);
        if (idx >= 0) mockCollections.splice(idx, 1);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      } else if (route.request().method() !== "OPTIONS") {
        await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
      } else {
        await route.fulfill({ status: 204 });
      }
    });

    // Mock taxonomies
    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { genres: [], tags: [], publishers: [], collections: ["Fantasy", "Sci-Fi"] },
        }),
      });
    });

    // Mock items
    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
          meta: { page: 1, pages: 1, total: 0, limit: 20 },
        }),
      });
    });

    await page.route("**/api/stats**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { works: 0, expressions: 0, manifestations: 0, items: 0 },
        }),
      });
    });

    await page.goto("/collection");
    await page.waitForLoadState("networkidle");
  });

  test("allows full CRUD operations on collections", async ({ page }) => {
    // Open Modal via "Manage Collections" menuitem in the user dropdown
    await page.getByLabel("User menu").click();
    await page.getByRole("menuitem", { name: "Manage Collections" }).click();
    const heading = page.getByRole("heading", { name: "Manage Collections" });
    await expect(heading).toBeVisible();

    // Scope to the modal dialog to avoid matching sidebar filter elements
    const modal = page.locator(".fixed.inset-0.z-50").filter({ has: heading });

    // Verify existing collections are listed
    await expect(modal.getByText("Fantasy")).toBeVisible();
    await expect(modal.getByText("Sci-Fi")).toBeVisible();

    // Create a new collection
    await modal.getByPlaceholder("New collection name").fill("Cyberpunk");
    await modal.getByRole("button", { name: "Add" }).click();

    // After creation, the input should be cleared and "Collection created" toast shown
    await expect(modal.getByPlaceholder("New collection name")).toHaveValue("");
    await expect(page.getByText("Collection created")).toBeVisible();

    // Update a collection name
    const fantasyRow = modal.locator(".flex.items-center.justify-between").filter({ hasText: "Fantasy" });
    await fantasyRow.getByTitle("Edit Name").click();
    await modal.locator('input[value="Fantasy"]').fill("High Fantasy");
    await modal.getByText("Save").click();

    // Verify the rename is reflected
    await expect(modal.getByText("High Fantasy")).toBeVisible();

    // Delete a collection
    page.on("dialog", d => d.accept());
    const sciFiRow = modal.locator(".flex.items-center.justify-between").filter({ hasText: "Sci-Fi" });
    await sciFiRow.getByTitle("Delete Collection").click();

    await expect(page.getByText("Collection removed")).toBeVisible();
  });
});
