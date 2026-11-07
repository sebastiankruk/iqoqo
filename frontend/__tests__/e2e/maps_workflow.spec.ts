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

test.describe("Cartographic Maps & Attachments Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // 0. Mock user session & config
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "carto-user",
            email: "cartographer@iqoqo.local",
            permissions: ["write:item", "update:item", "upload:cover"],
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
  });

  test("should display map metadata, open interactive map viewer modal, zoom/rotate", async ({ page }) => {
    const mockItem = {
      id: 99,
      manifestation_id: 199,
      status: "completed",
      collection_status: "available",
      is_owner: true,
      map_insert_present: true,
      meta: {
        title: "Atlas of Middle-earth",
        format: "atlas",
        category: "cartographic",
        map_scale: "1:1,000,000",
        map_projection: "Lambert Conformal",
        map_attachments: [
          {
            id: "map-att-1",
            title: "West of the Misty Mountains",
            type: "regional_map",
            image_url:
              "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect width='100' height='100' fill='green'/></svg>",
            scale: "1:500,000",
            projection: "Lambert",
          },
        ],
      },
      work: {
        id: 50,
        title: "Atlas of Middle-earth",
        authors: ["Karen Wynn Fonstad"],
      },
      expression: {
        id: 60,
        content_type: "cartographic",
        language: "en",
      },
      manifestation: {
        id: 199,
        format: "atlas",
        map_scale: "1:1,000,000",
        map_projection: "Lambert Conformal",
        map_attachments: [
          {
            id: "map-att-1",
            title: "West of the Misty Mountains",
            type: "regional_map",
            image_url:
              "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect width='100' height='100' fill='green'/></svg>",
            scale: "1:500,000",
            projection: "Lambert",
          },
        ],
      },
    };

    await page.route("**/api/items/99", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockItem }),
      });
    });

    await page.goto("/item/99");

    // 1. Verify Cartographic badges/metadata rendered
    await expect(page.getByText("West of the Misty Mountains")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("1:1,000,000").first()).toBeVisible();

    // 2. Click "Inspect Map" to open MapViewerModal
    const inspectBtn = page.getByRole("button", { name: "Inspect Map" });
    await expect(inspectBtn).toBeVisible();
    await inspectBtn.click();

    // 3. Verify modal elements
    const zoomInBtn = page.getByRole("button", { name: "Zoom In" });
    const zoomOutBtn = page.getByRole("button", { name: "Zoom Out" });
    const rotateBtn = page.getByRole("button", { name: "Rotate 90°" });

    await expect(zoomInBtn).toBeVisible();
    await expect(page.getByText("100%")).toBeVisible();

    // 4. Test zoom & rotate interactions
    await zoomInBtn.click();
    await expect(page.getByText("150%")).toBeVisible();

    await rotateBtn.click();

    await zoomOutBtn.click();
    await expect(page.getByText("100%")).toBeVisible();
  });

  test("should filter collection by 'Includes Map' facet", async ({ page }) => {
    // Mock items catalog endpoint
    await page.route("**/api/items*", async route => {
      const url = route.request().url();
      const hasMapParam = url.includes("has_map=true") || url.includes("has_map=1");

      const items = hasMapParam
        ? [
            {
              id: 99,
              manifestation_id: 199,
              status: "completed",
              collection_status: "available",
              is_owner: true,
              meta: {
                title: "Atlas of Middle-earth",
                format: "atlas",
                map_attachments: [{ id: "map-1", title: "Map 1" }],
              },
              work: { id: 50, title: "Atlas of Middle-earth", authors: ["Karen Wynn Fonstad"] },
            },
          ]
        : [
            {
              id: 99,
              manifestation_id: 199,
              status: "completed",
              collection_status: "available",
              is_owner: true,
              meta: { title: "Atlas of Middle-earth", format: "atlas" },
              work: { id: 50, title: "Atlas of Middle-earth", authors: ["Karen Wynn Fonstad"] },
            },
            {
              id: 100,
              manifestation_id: 200,
              status: "completed",
              collection_status: "available",
              is_owner: true,
              meta: { title: "The Hobbit", format: "book" },
              work: { id: 51, title: "The Hobbit", authors: ["J.R.R. Tolkien"] },
            },
          ];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: items,
          meta: {
            total_items: items.length,
            limit: 20,
            offset: 0,
            has_next: false,
          },
        }),
      });
    });

    await page.goto("/collection");

    // 1. Expand Maps & Supplements accordion if collapsed
    const mapsSection = page.getByRole("button", { name: /Maps & Supplements/i });
    if (await mapsSection.isVisible()) {
      await mapsSection.click();
    }

    // 2. Check "Includes Map" checkbox
    const hasMapCheckbox = page.getByLabel(/Includes Map/i);
    await expect(hasMapCheckbox).toBeVisible({ timeout: 10000 });
    await hasMapCheckbox.check();

    // 3. Verify URL updated with has_map=true
    await expect(page).toHaveURL(/has_map=true/);

    // 4. Verify Active Filter chip is displayed
    await expect(page.getByText("Includes Map").first()).toBeVisible();
  });
});
