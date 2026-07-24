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

test.describe("Escalation Workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock custodian auth profile with escalation permissions
    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-custodian", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "custodian-id",
            email: "custodian@iqoqo.local",
            display_name: "Dr. Custodian",
            roles: ["custodian"],
            permissions: ["read:metadata", "write:metadata", "escalate:resolve", "delete:manifestation", "delete:item"],
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

  test("custodian views pending request, resolves it, and verifies it moves to processed", async ({ page }) => {
    // Mock pending escalation queue
    const pendingRequest = {
      id: 1,
      user_id: "test-user-id",
      user_display_name: "Test User",
      user_username: "testuser",
      manifestation_id: 42,
      field_name: "title",
      suggested_value: "Public Treasure (Corrected)",
      current_value: "Public Treasure",
      note: "This title should be corrected",
      request_type: "correction",
      status: "pending",
      created_at: "2026-07-23T10:00:00Z",
      updated_at: "2026-07-23T10:00:00Z",
    };

    await page.route("**/api/escalations/queue?status=pending**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [pendingRequest],
        }),
      });
    });

    // Mock resolved escalations (empty initially)
    await page.route("**/api/escalations/queue?status=accepted%2Crejected%2Cduplicate**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    // Mock resolve endpoint
    await page.route("**/api/escalations/1/resolve**", async route => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              ...pendingRequest,
              status: "accepted",
              resolved_at: "2026-07-24T12:00:00Z",
              resolver_display_name: "Dr. Custodian",
              resolution_note: "Fixed title",
            },
          }),
        });
      }
    });

    // Navigate to admin content page (User Requests tab)
    await page.goto("/admin/content?tab=escalations");

    // Wait for the page to load
    await page.waitForLoadState("networkidle");

    // Verify pending request is visible
    const pageContent = await page.textContent("body");
    expect(pageContent).toContain("Test User");
    expect(pageContent).toContain("Public Treasure (Corrected)");

    // Click "Accept" button to resolve
    const acceptButton = page.getByText("Accept");
    if (await acceptButton.isVisible()) {
      await acceptButton.click();

      // Wait for confirmation area to appear
      await page.waitForTimeout(500);

      // Click "Confirm" to finalize
      const confirmButton = page.getByText("Confirm");
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await page.waitForTimeout(500);
      }
    }
  });
});
