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
import { expect, test, type APIRequestContext } from "@playwright/test";

const FLASK_API_URL = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";

// Valid 1x1 transparent PNG bytes so Pillow / validate_upload_file accepts the gallery upload
const ONE_PX_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=",
  "base64"
);

/**
 * Authenticate the seed E2E admin user and exchange the Flask JWT for Next.js cookies.
 *
 * @param request - Playwright API request context.
 * @returns Token and Bearer authorization headers for direct API setup calls.
 */
async function authenticateE2EAdmin(
  request: APIRequestContext
): Promise<{ token: string; authHeaders: Record<string, string> }> {
  const loginRes = await request.post(`${FLASK_API_URL}/auth/login`, {
    data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
  });
  expect(loginRes.ok(), `Admin login failed: ${loginRes.status()} ${await loginRes.text()}`).toBeTruthy();
  const { token } = (await loginRes.json()) as { token: string };
  const exchangeRes = await request.post("/api/auth-exchange", { data: { token } });
  expect(exchangeRes.ok(), `Cookie exchange failed: ${exchangeRes.status()}`).toBeTruthy();
  return { token, authHeaders: { Authorization: `Bearer ${token}` } };
}

test.describe("v1.2.0 E2E Journeys (C156, C157, C158, C164)", () => {
  test("C157 + C158: manages Item physical_location, URL filters, bulk-location, Manifestation gallery and stats", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    const { authHeaders } = await authenticateE2EAdmin(page.request);
    const stamp = Date.now();
    const titleA = `LocItemA_${stamp}`;
    const titleB = `LocItemB_${stamp}`;

    const createA = await page.request.post(`${FLASK_API_URL}/items/manual`, {
      headers: authHeaders,
      data: { Title: titleA, Authors: ["Location Author A"], Format: "text", visibility: "public" },
    });
    expect(createA.ok()).toBeTruthy();
    const itemAId = ((await createA.json()) as { data: { item_id: number } }).data.item_id;

    const createB = await page.request.post(`${FLASK_API_URL}/items/manual`, {
      headers: authHeaders,
      data: { Title: titleB, Authors: ["Location Author B"], Format: "text", visibility: "public" },
    });
    expect(createB.ok()).toBeTruthy();
    const itemBId = ((await createB.json()) as { data: { item_id: number } }).data.item_id;

    const detailA = await page.request.get(`${FLASK_API_URL}/items/${itemAId}`, { headers: authHeaders });
    expect(detailA.ok()).toBeTruthy();
    const manifAId = ((await detailA.json()) as { data: { manifestation_id: number } }).data.manifestation_id;

    // 1. Set physical_location via TaxonomyEditor on /item/[id]
    await page.goto(`/item/${itemAId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Tags & Genres" }).click();

    const locInput = page.getByLabel("Physical Location");
    await expect(locInput).toBeVisible();
    await locInput.fill("Study / Shelf 1");
    const putPromise = page.waitForResponse(
      resp => resp.url().includes(`/api/items/${itemAId}`) && resp.request().method() === "PUT"
    );
    await page.getByRole("button", { name: "Save", exact: true }).click();
    expect((await putPromise).ok()).toBeTruthy();

    await page.reload();
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Tags & Genres" }).click();
    await expect(page.getByLabel("Physical Location")).toHaveValue("Study / Shelf 1");

    // 2. Hydrate /collection?view=items&location=... across reload & verify filtering
    await page.goto(`/collection?view=items&location=${encodeURIComponent("Study / Shelf 1")}`);
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[data-testid="card-title"]', { hasText: titleA })).toBeVisible();
    await expect(page.locator('[data-testid="card-title"]', { hasText: titleB })).toHaveCount(0);

    await page.reload();
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("location=");
    await expect(page.locator('[data-testid="card-title"]', { hasText: titleA })).toBeVisible();
    await expect(page.locator('[data-testid="card-title"]', { hasText: titleB })).toHaveCount(0);

    // 3. Select itemB in /collection and assign bulk physical_location via BulkItemVisibilityToolbar
    await page.goto(`/collection?view=items&q=${encodeURIComponent(titleB)}`);
    await page.waitForLoadState("networkidle");
    const cardB = page.locator(`[data-testid="item-card"][data-item-id="${itemBId}"]`);
    await expect(cardB).toBeVisible();
    await cardB.getByRole("button", { name: "Select", exact: true }).click();

    await expect(page.getByTestId("bulk-item-visibility-toolbar")).toBeVisible();
    await page.getByTestId("bulk-location-trigger").click();
    const bulkPopover = page.getByTestId("bulk-location-popover");
    await expect(bulkPopover).toBeVisible();
    await bulkPopover.locator("input").fill("Living Room / Case B");

    const bulkPatchPromise = page.waitForResponse(
      resp => resp.url().includes("/api/items/bulk-location") && resp.request().method() === "PATCH"
    );
    await bulkPopover.getByRole("button", { name: "Apply", exact: true }).click();
    expect((await bulkPatchPromise).ok()).toBeTruthy();

    const updatedB = await page.request.get(`${FLASK_API_URL}/items/${itemBId}`, { headers: authHeaders });
    expect(updatedB.ok()).toBeTruthy();
    const updatedBJson = (await updatedB.json()) as { data: { physical_location: string | null } };
    expect(updatedBJson.data.physical_location).toBe("Living Room / Case B");

    // 4. C158: Upload supplementary gallery scan + mark itemA "read", then verify /manifestation/[id]
    const uploadImg = await page.request.post(`${FLASK_API_URL}/manifestations/${manifAId}/images`, {
      headers: authHeaders,
      multipart: {
        label: "Back Cover",
        source: "community",
        image: { name: "back-cover.png", mimeType: "image/png", buffer: ONE_PX_PNG },
      },
    });
    expect(uploadImg.status()).toBe(201);

    const markRead = await page.request.put(`${FLASK_API_URL}/items/${itemAId}`, {
      headers: authHeaders,
      data: { status: "read" },
    });
    expect(markRead.ok()).toBeTruthy();

    await page.goto(`/manifestation/${manifAId}`);
    await page.waitForLoadState("networkidle");

    const gallery = page.getByTestId("manifestation-covers-gallery");
    await expect(gallery).toBeVisible();
    await gallery.getByRole("button").first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Close cover preview" }).click();
    await expect(dialog).toHaveCount(0);

    const statsCard = page.getByTestId("manifestation-stats-card");
    await expect(statsCard).toBeVisible();
    await expect(statsCard.getByTestId("popularity-chart")).toBeVisible();
  });

  test("C156: mobile multi-server switcher adds and switches saved servers on /login", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
      (window as unknown as { CapacitorCustomPlatform?: { name: string } }).CapacitorCustomPlatform = { name: "ios" };
    });

    await page.route("https://alpha.iqoqo.test/api/health", route =>
      route.fulfill({ status: 200, json: { status: "ok" } })
    );
    await page.route("https://alpha.iqoqo.test/api/config", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { instance_name: "Alpha Library", version: "1.2.0" } },
      })
    );
    await page.route("https://beta.iqoqo.test/api/health", route =>
      route.fulfill({ status: 200, json: { status: "ok" } })
    );
    await page.route("https://beta.iqoqo.test/api/config", route =>
      route.fulfill({ status: 200, json: { success: true, data: { instance_name: "Beta Library", version: "1.2.0" } } })
    );
    await page.route("https://*.iqoqo.test/api/auth/providers", route =>
      route.fulfill({ status: 200, json: { google: false, apple: false } })
    );

    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Initial native onboarding screen prompts for the first instance URL
    await page.locator("#server-name-input").fill("Alpha Library");
    await page.locator("#server-url-input").fill("https://alpha.iqoqo.test");
    await page.getByRole("button", { name: "Verify connection" }).click();

    const changeServerBtn = page.getByRole("button", { name: "Change instance server" });
    await expect(changeServerBtn).toBeVisible();

    // Add second server -> becomes active
    await changeServerBtn.click();
    await expect(page.getByTestId("saved-servers-list")).toContainText("Alpha Library");
    await page.locator("#server-name-input").fill("Beta Library");
    await page.locator("#server-url-input").fill("https://beta.iqoqo.test");
    await page.getByRole("button", { name: "Verify connection" }).click();
    await expect(page.getByRole("button", { name: "Verify connection" })).toHaveCount(0);

    // Re-open switcher, verify both appear, and switch back to Alpha Library
    await changeServerBtn.click();
    const list = page.getByTestId("saved-servers-list");
    await expect(list).toContainText("Alpha Library");
    await expect(list).toContainText("Beta Library");

    const alphaRow = list.locator('[data-testid^="saved-server-"]').filter({ hasText: "Alpha Library" });
    await expect(alphaRow.getByRole("button", { name: "Switch" })).toBeVisible();
    await alphaRow.getByRole("button", { name: "Switch" }).click();

    await expect(page.getByRole("button", { name: "Verify connection" })).toHaveCount(0);
    const activeUrl = await page.evaluate(() => window.localStorage.getItem("iqoqo_instance_url"));
    expect(activeUrl).toBe("https://alpha.iqoqo.test");
  });

  test("C164: /graph?type=person deduplicates shared external LOD URI into one canonical lod node", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    const canonicalLodId = "lod:9e107d9d372bb682";
    await page.route("**/api/catalog/graph?**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            anchor: { entity_type: "person", entity_id: 7, node_id: "person:7" },
            mode: "neighborhood",
            nodes: [
              { id: "person:7", entity_type: "person", entity_id: 7, label: "Stephen King", hop: 0, is_anchor: true },
              { id: "work:11", entity_type: "work", entity_id: 11, label: "It", hop: 1, is_anchor: false },
              { id: "work:12", entity_type: "work", entity_id: 12, label: "The Shining", hop: 1, is_anchor: false },
              {
                id: canonicalLodId,
                entity_type: "lod",
                entity_id: 101,
                label: "Stephen King",
                external_uri: "https://dbpedia.org/resource/Stephen_King",
                hop: 1,
                is_anchor: false,
              },
            ],
            edges: [
              {
                id: "w11--p7",
                source: "work:11",
                target: "person:7",
                relation: "contributed_by",
                category: "contributors",
                label: "author",
              },
              {
                id: "w12--p7",
                source: "work:12",
                target: "person:7",
                relation: "contributed_by",
                category: "contributors",
                label: "author",
              },
              {
                id: "p7--lod",
                source: "person:7",
                target: canonicalLodId,
                relation: "same_as",
                category: "lod",
                label: "sameAs",
              },
              {
                id: "w11--lod",
                source: "work:11",
                target: canonicalLodId,
                relation: "same_as",
                category: "lod",
                label: "sameAs",
              },
            ],
            meta: {
              depth: 2,
              requested_depth: 2,
              max_nodes: 150,
              max_edges: 400,
              node_count: 4,
              edge_count: 4,
              truncated: false,
            },
          },
          error: null,
        },
      })
    );

    await page.goto("/graph?type=person&id=7");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("frbr-relation-graph-svg")).toBeVisible();
    const lodNodes = page.locator('[data-testid^="graph-node-lod:"]');
    await expect(lodNodes).toHaveCount(1);
    await expect(page.getByTestId(`graph-node-${canonicalLodId}`)).toBeVisible();
  });
});
