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

test.describe("Escalation target entity enrichment", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

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

  test("custodian review screen displays target entity details", async ({ page }) => {
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
      target_entity: {
        id: 42,
        title: "Public Treasure",
        type: "Manifestation",
        current_state: "book",
      },
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

    await page.goto("/admin/content?tab=escalations");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Public Treasure").first()).toBeVisible();
    await expect(page.getByText("Manifestation").first()).toBeVisible();
    await expect(page.getByText("#42").first()).toBeVisible();
    await expect(page.getByText("book").first()).toBeVisible();
  });
});
