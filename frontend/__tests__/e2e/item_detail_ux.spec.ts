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

const MOCK_ITEM = {
  id: 101,
  manifestation_id: 202,
  owner_id: "owner-1",
  is_owner: true,
  title: "Kind of Blue",
  status: "want_to_listen",
  collection_status: "available",
  cover_url: "/file.svg",
  cover_status: "ready",
  work: { id: 11, title: "Kind of Blue", authors: ["Miles Davis"], meta: {} },
  expression: { id: 12, content_type: "music", language: "en" },
  manifestation_meta: { format: "vinyl", cover_url: "/file.svg", cover_status: "ready" } as Record<string, unknown>,
  meta: { format: "vinyl", cover_status: "ready" } as Record<string, unknown>,
  added_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

test.describe("Item Detail UX Declutter & Replace Cover (C142)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "owner-1",
            email: "owner@example.com",
            roles: ["admin"],
            permissions: ["update:item", "upload:cover", "write:metadata", "delete:item", "regenerate:cover"],
          },
        },
      })
    );

    let currentItem = { ...MOCK_ITEM };

    await page.route("**/api/items/101**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: currentItem },
      })
    );

    await page.route("**/api/manifestations/202/cover", route => {
      currentItem = {
        ...currentItem,
        cover_url: "/static/covers/202_user.jpg",
        cover_status: "ready",
        manifestation_meta: {
          ...currentItem.manifestation_meta,
          cover_url: "/static/covers/202_user.jpg",
          cover_source: "user_photo",
          cover_status: "ready",
          cover_status_updated_at: "2026-11-24T11:00:00Z",
        },
        meta: {
          ...currentItem.meta,
          cover_url: "/static/covers/202_user.jpg",
          cover_source: "user_photo",
          cover_status: "ready",
          cover_status_updated_at: "2026-11-24T11:00:00Z",
        },
      };
      return route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            task_id: null,
            cover_url: "/static/covers/202_user.jpg",
            cover_source: "user_photo",
            cover_status: "ready",
            cover_status_updated_at: "2026-11-24T11:00:00Z",
          },
        },
      });
    });

    await page.route("**/api/work-parts/**", route =>
      route.fulfill({ status: 200, json: { success: true, data: [] } })
    );
  });

  for (const vp of [
    { name: "mobile", width: 390, height: 844 },
    { name: "desktop", width: 1280, height: 800 },
  ]) {
    test(`surfaces Explore Graph and primary CTA above the fold on ${vp.name}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/item/101", { waitUntil: "domcontentloaded" });

      const exploreGraph = page.getByTestId("explore-graph-link");
      const primaryCta = page.getByTestId("primary-consumption-cta");
      await expect(exploreGraph).toBeVisible();
      await expect(primaryCta).toBeVisible();
      await expect(page.getByRole("navigation", { name: "FRBR Hierarchy" })).toBeVisible();
      await expect(page.getByRole("button", { name: "FRBR Hierarchy" })).toHaveCount(0);

      const graphBox = await exploreGraph.boundingBox();
      const ctaBox = await primaryCta.boundingBox();
      expect(graphBox).not.toBeNull();
      expect(ctaBox).not.toBeNull();
      expect(graphBox!.y).toBeLessThan(vp.height);
      expect(ctaBox!.y).toBeLessThan(vp.height);
    });
  }

  test("opens Admin Actions dropdown inside accordion, expands LOD, and Replace Cover upload flow", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/item/101", { waitUntil: "domcontentloaded" });

    // Linked Open Data and Admin Actions start collapsed in the sidebar accordion
    await expect(page.getByTestId("semantic-links-compact")).toHaveCount(0);
    await expect(page.getByTestId("admin-actions-menu-trigger")).toHaveCount(0);

    await page.getByTestId("lod-accordion-toggle").click();
    await expect(page.getByTestId("semantic-links-compact")).toBeVisible();

    await page.getByTestId("admin-actions-accordion-toggle").click();
    // Open labeled Admin Actions DropdownMenu
    const adminTrigger = page.getByTestId("admin-actions-menu-trigger");
    await expect(adminTrigger).toBeVisible();
    await adminTrigger.click();
    await expect(page.getByRole("menuitem", { name: /Remove from library/i })).toBeVisible();
    await page.keyboard.press("Escape");

    // Open Manage dropdown -> Replace Cover -> upload via gallery-file-input
    await page.getByTestId("sidebar-manage-menu").click();
    await page.getByTestId("replace-cover-menu-item").click();
    await expect(page.getByTestId("confirm-choose-gallery")).toBeVisible();

    await page.getByTestId("gallery-file-input").setInputFiles({
      name: "cover.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-jpeg"),
    });

    await expect(page.locator('img[src*="/static/covers/202_user.jpg"]').first()).toBeVisible();
  });
});
