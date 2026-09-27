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

import { test, expect, type Page } from "@playwright/test";

const mockStats = {
  total_manifestations: 250,
  linked_manifestations: 180,
  unlinked_manifestations: 70,
  total_links: 420,
  by_authority: {
    dbpedia: 210,
    geonames: 120,
    wordnet: 90,
  },
};

const mockLogs = [
  {
    timestamp: "2026-09-27T12:00:00Z",
    manifestation_id: 101,
    title: "Dune",
    status: "SUCCESS",
    links_added: 3,
    authorities: ["dbpedia", "geonames", "wordnet"],
    error: null,
  },
  {
    timestamp: "2026-09-27T12:00:01Z",
    manifestation_id: 102,
    title: "Unknown Fanzine #4",
    status: "SKIPPED",
    links_added: 0,
    authorities: [],
    error: null,
  },
];

async function setupUser(page: Page, roles: string[], permissions: string[]) {
  await page.addInitScript(() => {
    window.localStorage.setItem("iqoqo-cookie-consent", "true");
  });

  await page
    .context()
    .addCookies([{ name: "iqoqo_session", value: "mock-session-lod", domain: "localhost", path: "/" }]);

  await page.route("**/api/profile**", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      json: {
        success: true,
        data: {
          id: "test-user-id",
          email: `${roles[0]}@iqoqo.local`,
          display_name: `${roles[0]} User`,
          roles,
          permissions,
        },
      },
    })
  );

  // Common mock routes
  await page.route("**/api/config**", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      json: { success: true, data: { maintenance_mode: false } },
    })
  );

  await page.route("**/api/escalations/my**", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      json: { success: true, data: [] },
    })
  );

  await page.route("**/api/**/admin/lod/stats", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      json: { success: true, data: mockStats },
    })
  );
}

test.describe("LOD Reconciliation Dashboard End-to-End Suite", () => {
  test("denies access to standard collector user", async ({ page }) => {
    await setupUser(page, ["collector"], ["read:metadata"]);
    await page.goto("/admin/lod");

    await expect(page.getByRole("heading", { name: /Access denied/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Back to dashboard/i })).toBeVisible();
  });

  test("allows Administrator to inspect metrics and trigger reconciliation", async ({ page }) => {
    await setupUser(page, ["admin"], ["config:internal", "refetch:metadata"]);

    let reconcileRequested = false;
    let pollCount = 0;

    await page.route("**/api/**/admin/lod/reconcile", route => {
      reconcileRequested = true;
      return route.fulfill({
        status: 202,
        contentType: "application/json",
        json: {
          success: true,
          data: {
            task_id: "test-task-admin",
            status: "pending",
            message: "Batch LOD reconciliation scheduled",
          },
        },
      });
    });

    await page.route("**/api/**/admin/lod/tasks/test-task-admin", route => {
      pollCount++;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        json: {
          success: true,
          data: {
            task_id: "test-task-admin",
            status: pollCount > 1 ? "completed" : "processing",
            state: pollCount > 1 ? "SUCCESS" : "PROGRESS",
            percentage: pollCount > 1 ? 100 : 50,
            total: 100,
            processed: pollCount > 1 ? 100 : 50,
            total_resolved: 45,
            counts: {
              dbpedia: 20,
              geonames: 15,
              wordnet: 10,
            },
            recent_logs: mockLogs,
          },
        },
      });
    });

    await page.goto("/admin/lod");

    // 1. Verify Header and Breadcrumbs
    await expect(page.getByRole("heading", { name: /LOD reconciliation/i })).toBeVisible();

    // 2. Verify Metric Cards
    await expect(page.getByTestId("metric-card-manifestations")).toContainText("250");
    await expect(page.getByTestId("metric-card-dbpedia")).toContainText("210");
    await expect(page.getByTestId("metric-card-geonames")).toContainText("120");
    await expect(page.getByTestId("metric-card-wordnet")).toContainText("90");

    // 3. Verify UX Button Density Constraint (<= 4 buttons on batch control card)
    const cardButtons = page.locator('[data-testid="lod-batch-control-card"] button');
    const buttonCount = await cardButtons.count();
    expect(buttonCount).toBeLessThanOrEqual(4);

    // 4. Trigger Batch Scan
    const startButton = page.getByTestId("lod-start-scan-button");
    await expect(startButton).toBeVisible();
    await startButton.click();

    expect(reconcileRequested).toBe(true);

    // 5. Verify Progress Bar and Live Audit Logs
    await expect(page.getByTestId("lod-progress-bar-container")).toBeVisible();
    await expect(page.getByTestId("lod-audit-log-card")).toBeVisible();
    await expect(page.getByText("Dune")).toBeVisible();
    await expect(page.getByText("SUCCESS")).toBeVisible();
  });

  test("allows Custodian to configure options and view log stream", async ({ page }) => {
    await setupUser(page, ["custodian"], ["refetch:metadata", "write:metadata"]);

    await page.goto("/admin/lod");

    await expect(page.getByRole("heading", { name: /LOD reconciliation/i })).toBeVisible();

    const startButton = page.getByTestId("lod-start-scan-button");
    // By default, "unlinked only" is active
    await expect(startButton).toContainText(/Scan unlinked/i);

    // Open options dropdown
    const optionsButton = page.getByTestId("lod-scan-options-button");
    await optionsButton.click();

    // Toggle off "Unlinked entities only" -> updates CTA to "Start full scan"
    const unlinkedOption = page.getByTestId("lod-option-unlinked-only");
    await expect(unlinkedOption).toBeVisible();
    await unlinkedOption.click();

    await expect(startButton).toContainText(/Start full scan/i);
  });
});
