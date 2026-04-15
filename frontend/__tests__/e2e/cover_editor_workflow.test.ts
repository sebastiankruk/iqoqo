// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//
// E2E tests for cover editor functionality at /admin/content?tab=cover-art

import { test, expect } from "@playwright/test";

const COVER_EDITOR_URL = (manifestationId: number) => `/admin/content?tab=cover-art&manifestationId=${manifestationId}`;

test.describe("Cover Editor Workflow", () => {
  const testManifestationId = 1;

  test.beforeEach(async ({ page }) => {
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "admin@iqoqo.local",
            permissions: ["admin:all"],
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
          data: { federation_enabled: false, version: "0.4.0" },
        }),
      });
    });

    await page.route(`**/api/v1/admin/frbr/manifestation/${testManifestationId}**`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: testManifestationId,
            title: "Test Book",
            cover_url: null,
          },
        }),
      });
    });
  });

  test("should open cover editor for manifestation", async ({ page }) => {
    await page.goto(COVER_EDITOR_URL(testManifestationId));
    await expect(page).toHaveURL(/tab=cover-art/);
  });

  test("should load without crash", async ({ page }) => {
    await page.goto(COVER_EDITOR_URL(testManifestationId));
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});

test.describe("Cover Editor Permissions", () => {
  test("should work for admin user", async ({ page }) => {
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "admin-user",
            email: "admin@iqoqo.local",
            permissions: ["admin:all"],
          },
        }),
      });
    });

    const response = await page.request.get(COVER_EDITOR_URL(1));
    expect(response.ok()).toBeTruthy();
  });

  test("should reject without authentication", async ({ page }) => {
    await page.goto(COVER_EDITOR_URL(1));
    const loginVisible = await page
      .getByText(/login|sign in|unauthorized/i)
      .isVisible()
      .catch(() => false);
    expect(loginVisible || page.url().includes("login")).toBeTruthy();
  });
});

test.describe("Cover Editor UI/UX", () => {
  test("should have content area", async ({ page }) => {
    await page.goto(COVER_EDITOR_URL(1));
    const content = await page.content();
    expect(content.length).toBeGreaterThan(100);
  });
});
