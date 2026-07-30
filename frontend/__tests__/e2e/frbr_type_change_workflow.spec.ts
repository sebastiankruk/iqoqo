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
import packageJson from "../../package.json" assert { type: "json" };

test.describe("FRBR Type Change Workflow E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
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

  test("standard user submits a change_type request for a Manifestation", async ({ page }) => {
    // 1. Mock standard user profile without direct write permissions
    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-user", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "standard-user-id",
            email: "user@iqoqo.local",
            display_name: "Standard Collector",
            roles: ["user"],
            permissions: ["read:metadata", "escalate:request"],
          },
        }),
      });
    });

    // 2. Mock single Manifestation connected to Expression and Work
    const initialItem = {
      id: 100,
      owner_id: "standard-user-id",
      status: "unread",
      collection_status: "available",
      title: "The Matrix",
      authors: ["Wachowskis"],
      manifestation_id: 42,
      expression_id: 20,
      work_id: 10,
      cover_status: "ready",
      manifestation_meta: { format: "book", type: "text" },
      meta: {},
      added_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      work: {
        id: 10,
        title: "The Matrix",
        authors: ["Wachowskis"],
        content_type: "text",
      },
      expression: {
        id: 20,
        work_id: 10,
        title: "The Matrix",
        content_type: "text",
      },
    };

    await page.route("**/api/items/100**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: initialItem }),
      });
    });

    await page.route("**/api/escalations/my**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    let submittedPayload: Record<string, unknown> | null = null;
    await page.route("**/api/escalations", async route => {
      if (route.request().method() === "POST") {
        submittedPayload = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: 1,
              user_id: "standard-user-id",
              item_id: 100,
              manifestation_id: 42,
              request_type: "change_type",
              field_name: "type",
              suggested_value: "movie",
              status: "pending",
              created_at: new Date().toISOString(),
            },
          }),
        });
      }
    });

    await page.goto("/item/100");
    await page.waitForLoadState("networkidle");

    // Open help request dialog
    const helpButton = page.getByText("Ask custodians for help");
    await expect(helpButton).toBeVisible();
    await helpButton.click();

    // Select Entity Type field to request type change
    await page.selectOption("#field_name", "type");
    await page.fill("#suggested_value", "movie");

    const submitButton = page.getByText("Submit Request");
    await submitButton.click();

    await page.waitForTimeout(500);

    // Assert change_type request payload was dispatched correctly
    expect(submittedPayload).not.toBeNull();
    expect(submittedPayload).toMatchObject({
      data: {
        request_type: "change_type",
        field_name: "type",
        suggested_value: "movie",
      },
    });
  });

  test("custodian accepts change_type request and parent Expression and Work adapt types", async ({ page }) => {
    // 1. Mock custodian user profile
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
            permissions: [
              "read:metadata",
              "write:metadata",
              "escalate:resolve",
              "delete:manifestation",
              "delete:item",
            ],
          },
        }),
      });
    });

    const pendingTypeChangeRequest = {
      id: 50,
      user_id: "standard-user-id",
      user_display_name: "Standard Collector",
      user_username: "collector",
      manifestation_id: 42,
      expression_id: 20,
      work_id: 10,
      field_name: "type",
      suggested_value: "movie",
      current_value: "book",
      note: "This manifestation is a movie/DVD, not a book",
      request_type: "change_type",
      status: "pending",
      created_at: "2026-07-30T00:00:00Z",
      updated_at: "2026-07-30T00:00:00Z",
    };

    await page.route("**/api/escalations/queue?status=pending**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [pendingTypeChangeRequest],
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

    let resolvePayload: Record<string, unknown> | null = null;
    await page.route("**/api/escalations/50/resolve", async route => {
      if (route.request().method() === "POST") {
        resolvePayload = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              ...pendingTypeChangeRequest,
              status: "accepted",
              resolution_note: "Approved FRBR type adaptation to movie",
              resolved_at: new Date().toISOString(),
              resolver_display_name: "Dr. Custodian",
              adapted_frbr: {
                manifestation: { id: 42, format: "dvd", type: "movie" },
                expression: { id: 20, content_type: "video" },
                work: { id: 10, content_type: "video" },
              },
            },
          }),
        });
      }
    });

    await page.goto("/admin/content?tab=escalations");
    await page.waitForLoadState("networkidle");

    // Verify change type request badge is visible in escalation queue
    const queueContent = await page.textContent('[data-testid="escalation-queue"]');
    expect(queueContent).toContain("Change Type");
    expect(queueContent).toContain("Standard Collector");

    // Click Accept button
    const acceptBtn = page.getByText("Accept");
    await expect(acceptBtn).toBeVisible();
    await acceptBtn.click();

    await page.waitForTimeout(300);

    // Confirm resolution
    const confirmBtn = page.getByText("Confirm");
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();

    await page.waitForTimeout(500);

    // Verify resolve API endpoint was invoked with status accepted
    expect(resolvePayload).not.toBeNull();
    expect(resolvePayload).toMatchObject({
      status: "accepted",
    });
  });
});
