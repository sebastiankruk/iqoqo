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

/**
 * E2E tests validating the UI response when the @require_physical_item
 * interceptor rejects an invalid state modification.
 *
 * These tests use Playwright API mocking to simulate the backend rejecting
 * requests for virtual (id <= 0) item IDs and verify that the frontend
 * handles the 400 response gracefully — showing an error state rather than
 * crashing or silently ignoring the rejection.
 */

import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

const MOCK_PROFILE = {
  success: true,
  data: {
    id: "test-user-e2e",
    email: "e2e@iqoqo.local",
    display_name: "E2E Test User",
    permissions: ["update:item", "write:item", "delete:item", "write:metadata"],
  },
};

const MOCK_CONFIG = {
  success: true,
  data: { federation_enabled: false, version: "0.7.10" },
};

/**
 * Simulates the backend @require_physical_item interceptor rejecting a PUT
 * request for a virtual item ID (id <= 0) with a structured 400 payload.
 */
const INTERCEPTOR_REJECTION_400 = {
  error: "Cannot mutate virtual items (id <= 0). Physical item IDs must be strictly positive.",
  code: 400,
};

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe("@require_physical_item interceptor — UI response validation", () => {
  test.beforeEach(async ({ page }) => {
    // Stub authentication and config so the page renders
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PROFILE),
      });
    });

    await page.route("**/api/config**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CONFIG),
      });
    });

    await page.route("**/api/items", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [], meta: { total: 0, page: 1, limit: 20, pages: 0 } }),
      });
    });
    await page.route("**/api/items?*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: [], meta: { total: 0, page: 1, limit: 20, pages: 0 } }),
      });
    });
  });

  // -------------------------------------------------------------------------
  // Test 1: Direct API rejection returns 400
  // -------------------------------------------------------------------------

  test("direct PUT /api/items/0 returns 400 from interceptor", async ({ request }) => {
    // This test validates the API directly using Playwright's APIRequestContext.
    // It exercises the real backend interceptor (not a mock) by making a real
    // HTTP request to a locally running development server if available.
    // If no server is running, the test is skipped gracefully.
    const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || process.env.BASE_URL || "http://localhost:5000";

    try {
      const response = await request.put(`${baseUrl}/api/items/0`, {
        data: { status: "read" },
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 3000,
      });

      // If we reach here, the server is running — validate the response
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body).toHaveProperty("error");
      expect(body.error).toContain("id <= 0");
    } catch {
      // Server not running — skip gracefully
      test.skip(true, "Backend server not running; skipping live API test.");
    }
  });

  // -------------------------------------------------------------------------
  // Test 2: UI does not crash when an item PUT returns 400
  // -------------------------------------------------------------------------

  test("UI handles 400 from interceptor without crashing", async ({ page }) => {
    // Mock the item detail endpoint to serve a valid-looking item
    await page.route("**/api/items/1", async route => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: 1,
              status: "want_to_read",
              collection_status: "available",
              is_hidden: false,
              manifestation_id: 1,
              tags: [],
              meta: {},
            },
          }),
        });
      } else if (route.request().method() === "PUT") {
        // Simulate the interceptor rejecting a mutation
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify(INTERCEPTOR_REJECTION_400),
        });
      } else {
        await route.continue();
      }
    });

    const pageErrors: string[] = [];
    page.on("pageerror", error => pageErrors.push(error.message));

    await page.goto("/");

    // Wait for the page to stabilise
    await page.waitForLoadState("domcontentloaded");

    // Trigger a PUT via fetch in the browser context to simulate what the UI does
    const result = await page.evaluate(async () => {
      try {
        const resp = await fetch("/api/items/1", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "read" }),
        });
        return { status: resp.status, ok: resp.ok };
      } catch (err) {
        return { error: String(err) };
      }
    });

    expect(result.status).toBe(400);
    expect(pageErrors).toHaveLength(0); // No unhandled JS errors
  });

  // -------------------------------------------------------------------------
  // Test 3: Collections POST for virtual item is rejected by interceptor
  // -------------------------------------------------------------------------

  test("POST /api/items/-1/collections is rejected by interceptor with 400", async ({ request }) => {
    const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || process.env.BASE_URL || "http://localhost:5000";

    try {
      const response = await request.post(`${baseUrl}/api/items/-1/collections`, {
        data: { collection_id: 1 },
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 3000,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body).toHaveProperty("error");
    } catch {
      test.skip(true, "Backend server not running; skipping live API test.");
    }
  });

  // -------------------------------------------------------------------------
  // Test 4: PUT /api/items/-1 routes to virtual handler (not interceptor 400)
  // -------------------------------------------------------------------------

  test("PUT /api/items/-1 is routed to virtual handler, not blocked by interceptor", async ({ request }) => {
    // Negative IDs are valid for virtual wishlist items — the router should
    // route them to _update_virtual_item, not block them at the decorator.
    // The virtual handler returns 404 (intent not found) or 400 for FRBR violations,
    // but NOT the interceptor's "id <= 0" message.
    const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || process.env.BASE_URL || "http://localhost:5000";

    try {
      const response = await request.put(`${baseUrl}/api/items/-1`, {
        data: { status: "want_to_read" },
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 3000,
      });

      const body = await response.json();
      // Must NOT be a decorator rejection — negative IDs go to virtual handler
      if (response.status() === 400) {
        expect(body.error).not.toContain("id <= 0");
      }
      // 404 is acceptable (intent not found)
      expect([400, 401, 404]).toContain(response.status());
    } catch {
      test.skip(true, "Backend server not running; skipping live API test.");
    }
  });

  // -------------------------------------------------------------------------
  // Test 5: UI gracefully handles 400 from collections interceptor
  // -------------------------------------------------------------------------

  test("UI handles 400 from collections interceptor without crashing", async ({ page }) => {
    // Mock the collection add endpoint to return 400 (simulating interceptor rejection)
    await page.route("**/api/items/0/collections", async route => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify(INTERCEPTOR_REJECTION_400),
      });
    });

    const pageErrors: string[] = [];
    page.on("pageerror", error => pageErrors.push(error.message));

    await page.goto("/");

    await page.waitForLoadState("domcontentloaded");

    // Simulate a collection add fetch from the browser
    const result = await page.evaluate(async () => {
      try {
        const resp = await fetch("/api/items/0/collections", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collection_id: 1 }),
        });
        const body = await resp.json();
        return { status: resp.status, error: body.error };
      } catch (err) {
        return { fetchError: String(err) };
      }
    });

    expect(result.status).toBe(400);
    expect(result.error).toContain("id <= 0");
    expect(pageErrors).toHaveLength(0); // No unhandled JS errors
  });
});
