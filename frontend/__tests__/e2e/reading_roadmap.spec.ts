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

test.describe("Reading Roadmap E2E Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Login via direct Flask API call (avoids Next.js proxy POST body issues)
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = await loginRes.json();
    await page.goto(`/api/auth-exchange?token=${token}`);
    await page.waitForURL(/\/(collection)?$/);
  });

  test("should allow a user to create, populate, and reorder a reading roadmap pipeline", async ({ page }) => {
    // Navigate to the primary roadmaps organizational panel
    await page.goto("/collection?view=roadmap");
    await page.click('[data-testid="create-roadmap-btn"]');

    // Formulate roadmap core attributes
    await page.fill('input[name="title"]', "Distributed Systems Mastery 2026");
    await page.fill(
      'textarea[name="description"]',
      "A rigorous track mapping out foundations of decentralized computing."
    );
    await page.click('button[type="submit"]');

    // Assert roadmap creation in UI layout tree
    const roadmapHeader = page.locator("h2", { hasText: "Distributed Systems Mastery 2026" });
    await expect(roadmapHeader).toBeVisible();

    // Inject items into the newly configured track instance
    // First Item: Ingesting a conceptual work node
    await page.click('[data-testid="add-to-roadmap-btn"]');
    const searchInput = page.locator('input[data-testid="item-search-input"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill("Designing Data-Intensive Applications");
    await page.locator('[data-testid="select-item-0"]').click();
    await page.click('[data-testid="confirm-add-item"]');
    await expect(page.locator('[data-testid="roadmap-item-card"]')).toHaveCount(1);

    // Second Item: Ingesting a sequential manifestation node
    await page.click('[data-testid="add-to-roadmap-btn"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill("Distributed Systems: Principles and Paradigms");
    await page.locator('[data-testid="select-item-0"]').click();
    await page.click('[data-testid="confirm-add-item"]');

    // Verify tracking sequence list layout hierarchy
    const roadmapItems = page.locator('[data-testid="roadmap-item-card"]');
    await expect(roadmapItems).toHaveCount(2);
    await expect(roadmapItems.nth(0)).toContainText("Designing Data-Intensive Applications");
    await expect(roadmapItems.nth(1)).toContainText("Distributed Systems: Principles and Paradigms");

    // Trigger mutation sequence reordering to assert spatial repositioning arithmetic execution
    const reorderResponsePromise = page.waitForResponse(
      res => res.url().includes("/position") && res.request().method() === "PATCH"
    );
    await roadmapItems.nth(1).hover();
    const moveUpButton = roadmapItems.nth(1).locator('[data-testid="move-up-btn"]');
    await moveUpButton.click();
    await reorderResponsePromise;

    // Assert DOM restructuring mirrors successful transactional order shift mutation execution
    await expect(roadmapItems.nth(0)).toContainText("Distributed Systems: Principles and Paradigms");
    await expect(roadmapItems.nth(1)).toContainText("Designing Data-Intensive Applications");

    // Persist verification through hard reload cycle bounds to ensure DB sync
    await page.reload();
    await expect(page.locator("h2", { hasText: "Distributed Systems Mastery 2026" })).toBeVisible();
    await expect(page.locator('[data-testid="roadmap-item-card"]').nth(0)).toContainText(
      "Distributed Systems: Principles and Paradigms"
    );
  });
});
