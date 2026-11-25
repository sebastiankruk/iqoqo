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

test.describe("FRBR Relation Graph Explorer E2E (C133)", () => {
  test("navigates from Work page via Explore Graph to /graph, filters edges, and recenters", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = (await loginRes.json()) as { token: string };
    const authHeaders = { Authorization: `Bearer ${token}` };

    const createRes = await page.request.post(`${flaskApiUrl}/items/manual`, {
      headers: authHeaders,
      data: {
        Title: "Graph Explorer Test Work",
        Authors: ["Graph Test Author"],
        Format: "text",
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const created = (await createRes.json()) as { data: { item_id: number } };

    const itemRes = await page.request.get(`${flaskApiUrl}/items/${created.data.item_id}`, {
      headers: authHeaders,
    });
    expect(itemRes.ok()).toBeTruthy();
    const itemJson = (await itemRes.json()) as {
      data: { work?: { id: number }; expression?: { id: number }; manifestation_id?: number };
    };
    const workId = itemJson.data.work?.id;
    const exprId = itemJson.data.expression?.id;
    const manifestationId = itemJson.data.manifestation_id;
    expect(workId).toBeTruthy();
    expect(exprId).toBeTruthy();
    expect(manifestationId).toBeTruthy();

    // Seed structured Contributor + WorkContribution for Person root picker & recentering
    const contribRes = await page.request.put(`${flaskApiUrl}/v1/admin/frbr/work/${workId}`, {
      headers: authHeaders,
      data: {
        meta: { authors: ["Graph Test Author"] },
        contributions: [{ name: "Graph Test Author", role: "author", sequence: 0 }],
      },
    });
    expect(contribRes.ok(), `contrib failed: ${contribRes.status()} ${await contribRes.text()}`).toBeTruthy();

    const exchangeRes = await page.request.post("/api/auth-exchange", { data: { token } });
    expect(exchangeRes.ok()).toBeTruthy();

    // 1. Verify top utility bar Explore Graph visibility & <= 4 buttons on mobile and desktop across Work, Expression, Manifestation
    const tiers: Array<{ type: "work" | "expression" | "manifestation"; id: number }> = [
      { type: "work", id: workId! },
      { type: "expression", id: exprId! },
      { type: "manifestation", id: manifestationId! },
    ];
    for (const viewport of [
      { width: 390, height: 844 },
      { width: 1280, height: 800 },
    ]) {
      await page.setViewportSize(viewport);
      for (const tier of tiers) {
        await page.goto(`/${tier.type}/${tier.id}`);
        await page.waitForLoadState("networkidle");
        const exploreBtn = page.getByTestId("explore-graph-link");
        await expect(exploreBtn).toBeVisible();
        await expect(exploreBtn).toHaveAttribute("href", `/graph?type=${tier.type}&id=${tier.id}`);
        const box = await exploreBtn.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.y).toBeLessThan(viewport.height);
        const barButtonsCount = await exploreBtn
          .locator(
            "xpath=ancestor::div[contains(@class,'border-b')][1]//a | ancestor::div[contains(@class,'border-b')][1]//button"
          )
          .count();
        expect(barButtonsCount).toBeLessThanOrEqual(4);
      }
    }

    // 2. Visit Work page and click Explore Graph
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`/work/${workId}`);
    await page.waitForLoadState("networkidle");

    const exploreBtn = page.getByTestId("explore-graph-link");
    await expect(exploreBtn).toBeVisible();
    await exploreBtn.click();

    await page.waitForURL(`**/graph?type=work&id=${workId}**`);
    await expect(page.getByTestId("frbr-relation-graph-svg")).toBeVisible();
    await expect(page.getByTestId(`graph-node-work:${workId}`)).toBeVisible();
    await expect(page.getByTestId(`graph-node-expression:${exprId}`)).toBeVisible();

    // 2. Open filter popover and toggle FRBR filter off -> expression node disappears, then restore
    await page.getByTestId("graph-filters-trigger").click();
    await page.getByTestId("graph-filter-frbr").click();
    await expect(page.getByTestId(`graph-node-expression:${exprId}`)).not.toBeVisible();
    await page.getByTestId("graph-filter-frbr").click();
    await expect(page.getByTestId(`graph-node-expression:${exprId}`)).toBeVisible();

    // 3. Click Expression node to inspect and recenter on it
    await page.getByTestId(`graph-node-expression:${exprId}`).click();
    await expect(page.getByTestId("graph-recenter-button")).toBeVisible();
    await page.getByTestId("graph-recenter-button").click();

    await page.waitForURL(`**/graph?type=expression&id=${exprId}**`);
    await expect(page.getByTestId(`graph-node-expression:${exprId}`)).toBeVisible();

    // 4. Use Switch Root dialog to search and pick the Author (Person) root
    await page.getByTestId("graph-switch-root-button").click();
    const pickerInput = page.getByTestId("graph-picker-input");
    await expect(pickerInput).toBeVisible();
    await pickerInput.fill("Graph Test Author");
    const personOption = page.locator('[data-testid^="graph-picker-option-person:"]').first();
    await expect(personOption).toBeVisible();
    await personOption.click();

    await page.waitForURL("**/graph?type=person&id=*");
    await expect(page.getByTestId("frbr-relation-graph-svg")).toBeVisible();
  });

  test("unauthenticated visitor cannot see private items in graph root picker search (C143)", async ({ page }) => {
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = (await loginRes.json()) as { token: string };

    const uniqueTitle = `PrivateGraphPickerItem_${Date.now()}`;
    const createRes = await page.request.post(`${flaskApiUrl}/items/manual`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        Title: uniqueTitle,
        Authors: ["Private Author"],
        Format: "text",
        visibility: "private",
      },
    });
    expect(createRes.ok()).toBeTruthy();

    // Unauthenticated API search for items must omit the private item
    const searchRes = await page.request.get(
      `${flaskApiUrl}/catalog/graph/search?q=${encodeURIComponent(uniqueTitle)}&types=item`
    );
    expect(searchRes.ok()).toBeTruthy();
    const searchJson = (await searchRes.json()) as { data: Array<{ label: string }> };
    expect(searchJson.data).toEqual([]);
  });
});
