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

test.describe("Serial & Magazine Scanner + Issues Browser (C132)", () => {
  test("bare 977 lookup opens serial disambiguation modal and pre-fills new issue entry", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-serial", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "serial-user",
            email: "serial@iqoqo.local",
            display_name: "Serial Collector",
            permissions: ["write:item", "update:item", "write:metadata"],
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
          data: { federation_enabled: false, version: "1.1.0" },
        }),
      });
    });

    await page.route("**/api/manifestations/recent**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route("**/api/lookup/9771507596044**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            status: "serial_disambiguation",
            serial_disambiguation: true,
            title: "National Geographic Polska",
            authors: ["Towarzystwo National Geographic"],
            publisher: "G+J RBA",
            format: "magazine",
            work_kind: "serial",
            issn: "1507-5966",
            ean: "9771507596044",
            work: { id: 50, title: "National Geographic Polska", issn: "1507-5966", work_kind: "serial" },
            existing_issues: [
              {
                manifestation_id: 501,
                issue_number: "7",
                cumulative_issue_number: 58,
                publication_year: 2004,
                publication_month: 7,
                ean_addon: "07",
                full_barcode: "977150759604407",
                cover_headline: "Skarby pod lodem",
              },
            ],
            prefill: {
              title: "National Geographic Polska",
              authors: ["Towarzystwo National Geographic"],
              publisher: "G+J RBA",
              format: "magazine",
              issn: "1507-5966",
              ean: "9771507596044",
            },
          },
        }),
      });
    });

    const capturedRequests: Record<string, unknown>[] = [];
    await page.route("**/api/items/manual**", async route => {
      capturedRequests.push(route.request().postDataJSON() as Record<string, unknown>);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 702,
            manifestation_id: 502,
          },
        }),
      });
    });

    await page.goto("/scan");
    await page.waitForLoadState("networkidle");

    const lookupInput = page.getByTestId("unified-lookup-input");
    await lookupInput.fill("9771507596044");
    await page.keyboard.press("Enter");

    const modal = page.getByTestId("serial-disambiguation-modal");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("National Geographic Polska");
    await expect(modal).toContainText("ISSN 1507-5966");
    await expect(modal).toContainText("7(58)");
    await expect(modal).toContainText("Skarby pod lodem");

    await page.getByTestId("add-new-serial-issue-button").click();

    await expect(page.locator("#manual-issn")).toHaveValue("1507-5966");
    await page.locator("#manual-issue-number").fill("12");
    await page.locator("#manual-cumulative-issue").fill("63");
    await page.locator("#manual-publication-month").fill("12");
    await page.locator("#manual-ean-addon").fill("12");
    await page.locator("#manual-cover-headline").fill("Zagadka znikających pszczół");

    await page.locator('button[type="submit"]').first().click();

    await expect.poll(() => capturedRequests.length).toBeGreaterThan(0);
    const capturedManualBody = capturedRequests[0];
    expect(capturedManualBody?.issn).toBe("1507-5966");
    expect(capturedManualBody?.Format).toBe("text");
    expect(capturedManualBody?.work_kind).toBe("serial");
    expect(capturedManualBody?.issue_number).toBe("12");
    expect(capturedManualBody?.cumulative_issue_number).toBe(63);
  });

  test("serial work detail displays chronological Issues in this Serial section and Add Issue CTA", async ({
    page,
  }) => {
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

    const createIssue1 = await page.request.post(`${flaskApiUrl}/items/manual`, {
      headers: authHeaders,
      data: {
        Title: "National Geographic Polska",
        Authors: ["Towarzystwo National Geographic"],
        Format: "text",
        work_kind: "serial",
        issn: "1507-5966",
        ean: "9771507596044",
        ean_addon: "07",
        issue_number: "7",
        cumulative_issue_number: 58,
        publication_year: 2004,
        publication_month: 7,
        cover_headline: "Skarby pod lodem",
      },
    });
    expect(createIssue1.ok()).toBeTruthy();
    const issue1Body = (await createIssue1.json()) as { data: { item_id: number } };

    const createIssue2 = await page.request.post(`${flaskApiUrl}/items/manual`, {
      headers: authHeaders,
      data: {
        Title: "National Geographic Polska",
        Authors: ["Towarzystwo National Geographic"],
        Format: "text",
        work_kind: "serial",
        issn: "1507-5966",
        ean: "9771507596501",
        ean_addon: "01",
        issue_number: "1",
        cumulative_issue_number: 64,
        publication_year: 2005,
        publication_month: 1,
        cover_headline: "Rok pod znakiem wielkich zmian",
      },
    });
    expect(createIssue2.ok()).toBeTruthy();

    const itemResp = await page.request.get(`${flaskApiUrl}/items/${issue1Body.data.item_id}`, {
      headers: authHeaders,
    });
    expect(itemResp.ok()).toBeTruthy();
    const itemJson = (await itemResp.json()) as { data: { work?: { id: number } } };
    const workId = itemJson.data.work?.id;
    expect(workId).toBeTruthy();

    const exchangeRes = await page.request.post("/api/auth-exchange", { data: { token } });
    expect(exchangeRes.ok()).toBeTruthy();

    await page.goto(`/work/${workId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("work-add-issue-cta")).toBeVisible();
    const section = page.getByTestId("serial-issues-section");
    await expect(section).toBeVisible();
    await expect(section).toContainText("Issues in this Serial");
    await expect(section).toContainText("7 (58)");
    await expect(section).toContainText("1 (64)");
    await expect(section).toContainText("Skarby pod lodem");
  });
});
