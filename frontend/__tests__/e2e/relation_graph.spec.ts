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
      data: { work?: { id: number }; expression?: { id: number } };
    };
    const workId = itemJson.data.work?.id;
    const exprId = itemJson.data.expression?.id;
    expect(workId).toBeTruthy();
    expect(exprId).toBeTruthy();

    const exchangeRes = await page.request.post("/api/auth-exchange", { data: { token } });
    expect(exchangeRes.ok()).toBeTruthy();

    // 1. Visit Work page and click Explore Graph
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
  });
});
