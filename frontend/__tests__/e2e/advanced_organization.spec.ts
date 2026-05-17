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

test.describe("Advanced Organization & Views - Step 2", () => {
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

  test("identical manifestations are visually grouped with a quantity badge", async ({ page }) => {
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

    await page.route("**/api/items*", async route => {
      const json = {
        success: true,
        data: [
          {
            id: 1,
            manifestation_id: 100,
            title: "Dune",
            authors: ["Frank Herbert"],
            status: "want_to_read",
            collection_status: "available",
            meta: {},
          },
          {
            id: 2,
            manifestation_id: 100,
            title: "Dune",
            authors: ["Frank Herbert"],
            status: "read",
            collection_status: "available",
            meta: {},
          },
          {
            id: 3,
            manifestation_id: 101,
            title: "Dune Messiah",
            authors: ["Frank Herbert"],
            status: "read",
            collection_status: "available",
            meta: {},
          },
        ],
        meta: {
          total: 3,
          page: 1,
          pages: 1,
          limit: 40,
        },
      };
      await route.fulfill({ json });
    });

    await page.goto("/collection");

    // Use data-testid="card-title" which only appears in the card info section,
    // not in the decorative cover placeholder span.
    await expect(page.getByTestId("card-title").filter({ hasText: "Dune Messiah" }).first()).toBeVisible();

    // Only one grouped card for "Dune" (manifestation_id=100 x2 should be deduplicated)
    const duneCards = page.getByTestId("card-title").filter({ hasText: /^Dune$/ });
    await expect(duneCards).toHaveCount(1);

    const badge = page.getByText("x2");
    await expect(badge).toBeVisible();
  });

  test("clicking an author navigates to a filtered discovery view", async ({ page }) => {
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

    await page.route("**/api/items*", async route => {
      const json = {
        success: true,
        data: [
          {
            id: 1,
            manifestation_id: 100,
            title: "Foundation",
            authors: ["Isaac Asimov"],
            status: "read",
            collection_status: "available",
            meta: {},
          },
        ],
        meta: {
          total: 1,
          page: 1,
          pages: 1,
          limit: 40,
        },
      };
      await route.fulfill({ json });
    });

    await page.goto("/collection");

    // Author links are rendered inside the card – click the first matching one
    const authorLink = page.getByText("Isaac Asimov").first();
    await expect(authorLink).toBeVisible();

    await authorLink.click();

    await page.waitForURL("**/collection?q=Isaac+Asimov*");

    // Target the main collection search box specifically (not the Navbar search)
    const searchInput = page.getByPlaceholder("Search your collection...");
    if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(searchInput).toHaveValue("Isaac Asimov");
    }
  });

  test("bulk add API endpoint successfully accepts strict payloads", async ({ request }) => {
    // Use the dedicated E2E admin seeded by tests/e2e/scripts/seed_e2e.py.
    // This user is always upserted with a known password so the test works
    // with the live local DB (VS Code) and after a db-reset (make test-e2e).
    const loginRes = await request.post("/api/auth/login", {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });

    expect(loginRes.ok()).toBeTruthy();
    const tokenData = await loginRes.json();
    const token = tokenData.token;

    const manRes = await request.get("/api/public/manifestations?limit=2");
    expect(manRes.ok()).toBeTruthy();

    const manData = await manRes.json();
    if (manData.data && manData.data.length >= 2) {
      const ids = [manData.data[0].id, manData.data[1].id];

      const bulkRes = await request.post("/api/items/bulk", {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          manifestation_ids: ids,
          status: "want_to_read",
          collection_status: "wish_list",
        },
      });

      expect(bulkRes.status()).toBe(200);
      const bulkJson = await bulkRes.json();

      expect(bulkJson.success).toBe(true);
      expect(bulkJson.data.item_ids.length).toBe(2);

      const badBulkRes = await request.post("/api/items/bulk", {
        headers: { Authorization: `Bearer ${token}` },
        data: { manifestation_ids: [] },
      });
      expect(badBulkRes.status()).toBe(400);
    }
  });

  test("infinite scrolling triggers next page load on scroll", async ({ page }) => {
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

    // Single handler avoids glob-ambiguity where ?*page=2* could match page-1
    // requests whose URL lacks an explicit page param, loading both pages at once.
    let page2Requested = false;
    await page.route("**/api/items**", async route => {
      const url = new URL(route.request().url());
      const pageParam = parseInt(url.searchParams.get("page") || "1", 10);
      if (pageParam >= 2) {
        page2Requested = true;
        await route.fulfill({
          json: {
            success: true,
            data: [
              {
                id: 2,
                manifestation_id: 101,
                title: "Page Two Book",
                authors: ["Author B"],
                status: "read",
                collection_status: "available",
                meta: {},
              },
            ],
            meta: { total: 2, page: 2, pages: 2, limit: 40 },
          },
        });
      } else {
        await route.fulfill({
          json: {
            success: true,
            data: [
              {
                id: 1,
                manifestation_id: 100,
                title: "Page One Book",
                authors: ["Author A"],
                status: "read",
                collection_status: "available",
                meta: {},
              },
            ],
            meta: { total: 2, page: 1, pages: 2, limit: 40 },
          },
        });
      }
    });

    await page.goto("/collection");

    // data-testid="card-title" only targets the card info p, not the decorative cover placeholder span
    await expect(page.getByTestId("card-title").filter({ hasText: "Page One Book" }).first()).toBeVisible();
    await expect(page.getByTestId("card-title").filter({ hasText: "Page Two Book" })).toHaveCount(0);

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    await expect(page.getByTestId("card-title").filter({ hasText: "Page Two Book" }).first()).toBeVisible();
    expect(page2Requested).toBe(true);
  });

  test("advanced view API endpoints (taxonomies, works) respond correctly", async ({ request }) => {
    // Use the dedicated E2E admin seeded by tests/e2e/scripts/seed_e2e.py.
    const loginRes = await request.post("/api/auth/login", {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });

    expect(loginRes.ok()).toBeTruthy();
    const { token } = await loginRes.json();

    const taxRes = await request.get("/api/taxonomies", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(taxRes.status()).toBe(200);

    const taxJson = await taxRes.json();
    expect(taxJson.success).toBe(true);
    expect(Array.isArray(taxJson.data.tags)).toBe(true);
    expect(Array.isArray(taxJson.data.genres)).toBe(true);
    expect(Array.isArray(taxJson.data.publishers)).toBe(true);

    const worksRes = await request.get("/api/works/shelf", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(worksRes.status()).toBe(200);

    const worksJson = await worksRes.json();
    expect(worksJson.success).toBe(true);
    expect(Array.isArray(worksJson.data)).toBe(true);

    if (worksJson.data.length > 0) {
      expect(worksJson.data[0]).toHaveProperty("work_id");
      expect(worksJson.data[0]).toHaveProperty("total_items");
      expect(Array.isArray(worksJson.data[0].owned_manifestations)).toBe(true);
    }
  });
});
