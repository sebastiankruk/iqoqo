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

test.describe("Phase 3 DevOps & UI Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock Profile to bypass login redirects
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "admin-id",
            email: "admin@iqoqo.local",
            display_name: "Admin User",
            roles: ["admin"],
            permissions: ["config:internal", "write:metadata"],
          },
        },
      })
    );

    // Mock Config
    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false, version: "0.6.0" } },
      })
    );

    // Mock Settings
    await page.route("**/v1/admin/settings*", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            MAINTENANCE_MODE: { value: "false", source: "db" },
            IQOQO_KNOWN_JUNK_PHASHES: { value: "", source: "db" },
          },
        },
      })
    );
  });

  test("Landing page has functional GitHub link", async ({ page }) => {
    // Un-mock profile or mock as 401 to see the landing page Hero
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 401,
        json: { success: false, error: "Unauthorized" },
      })
    );

    await page.goto("/");
    const githubLink = page.getByRole("link", { name: "GitHub", exact: true });
    await expect(githubLink).toBeVisible();
    await expect(githubLink).toHaveAttribute("href", "https://github.com/sebastiankruk/iqoqo");
    await expect(githubLink).toHaveAttribute("target", "_blank");
  });

  test("Admin internal settings show Maintenance Mode toggle", async ({ page }) => {
    // Note: This requires admin login which is mocked in beforeEach
    await page.goto("/admin/settings?tab=instance");

    // Check if the Maintenance Mode card exists
    await expect(page.getByText("Maintenance Mode")).toBeVisible();
    await expect(page.locator("select")).toBeVisible();
  });
});

// ── AdBlocker Resilience ───────────────────────────────────────────────────────

test.describe("Phase 3 — OpenObserve AdBlocker Resilience", () => {
  /**
   * This suite verifies that the application renders correctly even when a
   * browser ad-blocker blocks all OpenObserve RUM and OTel collector endpoints.
   * Graceful degradation means: no white-screen, navigation is visible,
   * and the JS error boundary is never triggered.
   */

  test("App loads successfully even if OpenObserve is blocked by an ad-blocker", async ({ page }) => {
    // 1. Simulate an ad-blocker aborting all requests to OpenObserve origins
    await page.route("**/*openobserve*", route => route.abort("blockedbyclient"));
    await page.route("**/*o2jam*", route => route.abort("blockedbyclient"));

    // 2. Mock profile as unauthenticated so we land on the public hero
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 401,
        json: { success: false, error: "Unauthorized" },
      })
    );

    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: { federation_enabled: false, version: packageJson.version } },
      })
    );

    // 3. Verify no console errors that reference a JS crash from RUM init
    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/");

    // 4. Core assertions: body and navigation must be visible
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByRole("navigation")).toBeVisible();

    // 5. The page must NOT be a blank white-screen (detect React error boundary)
    const errorBoundaryText = page.locator("[data-testid='error-boundary-fallback']");
    await expect(errorBoundaryText).toHaveCount(0);

    // 6. No uncaught exceptions from the RUM SDK init should appear as errors
    const rumCrashErrors = consoleErrors.filter(
      e => e.toLowerCase().includes("uncaught") && e.toLowerCase().includes("openobserve")
    );
    expect(rumCrashErrors).toHaveLength(0);
  });
});

// ── FRBR Virtual Item QR Code Boundary ────────────────────────────────────────

test.describe("Phase 3 — FRBR Wishlist QR Code Boundary", () => {
  /**
   * Enforces the FRBR ontology rule:
   *   Virtual items (id < 0) are UserWorkIntent adapters with no physical copy.
   *   They must NEVER expose a QR Code generation button.
   *
   * This test intercepts the item API response and forces a wishlist state
   * to validate that the frontend component correctly hides the QR Code button.
   */

  test.beforeEach(async ({ page }) => {
    // Authenticate as a normal item owner
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "owner-user-id",
            email: "owner@iqoqo.local",
            permissions: ["update:item", "write:metadata", "upload:cover"],
            roles: [],
          },
        },
      })
    );

    await page.route("**/api/config**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: { federation_enabled: false, version: packageJson.version },
        },
      })
    );
  });

  test("Wishlist items do not display a QR Code button", async ({ page }) => {
    // 1. Mock GET /api/items/-1 to return a virtual wishlist item payload
    await page.route("**/api/items/-1**", async route => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: -1,
            title: "Virtual Wishlist Book",
            status: "want_to_read",
            collection_status: "wish_list",
            manifestation_id: null,
            is_owner: true,
            owner_id: "owner-user-id",
            meta: { format: "book" },
          },
        }),
      });
    });

    // 2. Virtual item logs return an empty array (expected FRBR contract)
    await page.route("**/api/items/-1/logs**", route =>
      route.fulfill({
        status: 200,
        json: { success: true, data: [] },
      })
    );

    await page.goto("/item/-1");
    await page.waitForLoadState("networkidle");

    // 3. Assert QR Code button is ABSENT for the virtual wishlist item
    await expect(page.getByTestId("qrcode-btn")).toHaveCount(0);
    await expect(page.locator("button", { hasText: "Print QR Code" })).toHaveCount(0);
  });
});
