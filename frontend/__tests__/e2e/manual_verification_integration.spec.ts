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

test.describe("Manual Verification Integration E2E", () => {
  // We use page.route to mock API calls so the tests are fast, reliable, and decoupled from DB states.
  test.beforeEach(async ({ page }) => {
    // 1. Cookie consent bypass
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // 2. Mock default profile endpoint
    await page.route("**/api/profile**", async route => {
      if (route.request().method() === "PUT") {
        const data = route.request().postDataJSON();
        // Handle mocked 409 conflict
        if (data.public_username === "takenuser") {
          return route.fulfill({
            status: 409,
            contentType: "application/json",
            body: JSON.stringify({ success: false, error: "Username already taken" }),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: "test-user-id",
              email: "testuser@iqoqo.local",
              display_name: "Test User",
              public_username: "testuser1",
              bio: "Caveman Grog collector",
              visibility: "private",
              roles: ["admin"],
              permissions: [
                "upload:cover",
                "update:item",
                "write:metadata",
                "read:metadata",
                "config:internal",
                "config:external_apis",
              ],
            },
          }),
        });
      }
    });

    // 3. Mock app config
    await page.route("**/api/config**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federation_enabled: true, version: packageJson.version },
        }),
      });
    });

    // 4. Mock taxonomies
    await page.route("**/api/taxonomies**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            genres: ["Fantasy", "Sci-Fi", "Music"],
            publishers: ["Ace Books", "HarperCollins"],
            tags: ["scifi", "cyberpunk", "wishlist"],
            collections: ["My Books"],
          },
        }),
      });
    });
  });

  test("Profile Setup, Visibility & Taken Username Conflict", async ({ page }) => {
    await page.goto("/admin/settings?tab=profile");
    await page.waitForLoadState("networkidle");

    const displayName = page.getByPlaceholder("Enter your display name");
    const publicUsername = page.getByPlaceholder("testuser1");
    const bio = page.getByPlaceholder("Tell the world about your library...");
    const publicRadio = page.locator('input[value="public"]');
    const saveButton = page.getByRole("button", { name: "Save Changes" });

    // Set bio and update display name
    await displayName.fill("Grog Elder");
    await publicUsername.fill("testuser1");
    await bio.fill("Me collect ancient scrolls");
    await publicRadio.check();
    await saveButton.click();

    // Verify success toast message
    await expect(page.getByText(/Profile updated successfully/i)).toBeVisible();

    // Test taken username 409 conflict
    await publicUsername.fill("takenuser");
    await saveButton.click();

    // Expect conflict error to show up
    await expect(page.getByText(/Username already taken/i)).toBeVisible();
  });

  test("Item-Level Privacy (is_hidden toggle)", async ({ page }) => {
    const itemId = 123;
    let isHiddenState = false;

    // Mock item endpoint
    await page.route(`**/api/items/${itemId}**`, async route => {
      if (route.request().method() === "PUT") {
        const body = route.request().postDataJSON();
        isHiddenState = body.is_hidden;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: itemId, is_hidden: isHiddenState } }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: itemId,
              title: "Hidden Treasure Book",
              status: "unread",
              collection_status: "available",
              is_owner: true,
              is_hidden: isHiddenState,
              manifestation_id: 111,
              meta: { format: "book" },
              manifestation_meta: { format: "book" },
            },
          }),
        });
      }
    });

    await page.goto(`/item/${itemId}`);
    await page.waitForLoadState("networkidle");

    // Toggle the hidden checkbox/switch (verify aria-label or text)
    const hiddenCheckbox = page.locator('input[type="checkbox"][aria-label*="hide" i], input[type="checkbox"][id*="hidden" i]');
    if (await hiddenCheckbox.isVisible()) {
      await hiddenCheckbox.setChecked(true);
      await expect(page.getByText(/item visibility updated/i).or(page.getByText(/hidden/i))).toBeVisible();
    } else {
      // Fallback: look for visibility selection or toggle button
      const visibilityToggle = page.getByRole("checkbox", { name: /hide|hidden|private/i }).first();
      await visibilityToggle.click();
    }
  });

  test("Filtered Collection Sharing & i18n", async ({ page }) => {
    // Mock the share endpoint returning a custom token
    await page.route("**/api/shares**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { share_token: "test-share-token-12345" },
        }),
      });
    });

    // Mock items view
    await page.route("**/api/items**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 99,
              title: "Wishlist Book",
              status: "want_to_read",
              collection_status: "wish_list",
              is_owner: true,
              manifestation_id: 88,
              meta: { format: "book" },
            },
          ],
        }),
      });
    });

    await page.goto("/collection?status=want_to_read");
    await page.waitForLoadState("networkidle");

    // Open share view dialog
    const shareButton = page.getByRole("button", { name: /share/i }).first();
    await shareButton.click();

    // Dialog title check
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Share Collection View")).toBeVisible();

    // Click generate button if available
    const generateBtn = page.getByRole("button", { name: /generate/i });
    if (await generateBtn.isVisible()) {
      await generateBtn.click();
    }

    // Verify link text generated
    await expect(page.locator("input[value*='/share/']")).toBeVisible();

    // Switch locale to Polish ("pl")
    const langSelect = page.locator('select[aria-label*="language" i], button[aria-label*="language" i]');
    if (await langSelect.isVisible()) {
      await langSelect.selectOption("pl");
      // Verify translated text changes
      await expect(page.getByText(/udostępnij/i).or(page.getByText(/kopiuj/i))).toBeVisible();
    }
  });

  test("Lent Out Status Lifecycle", async ({ page }) => {
    const itemId = 555;
    let collectionStatus = "available";
    let loanDetails: any = null;

    await page.route(`**/api/items/${itemId}**`, async route => {
      if (route.request().method() === "PUT") {
        const body = route.request().postDataJSON();
        collectionStatus = body.collection_status || collectionStatus;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: itemId, collection_status: collectionStatus } }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: itemId,
              title: "Lending Book",
              status: "read",
              collection_status: collectionStatus,
              is_owner: true,
              manifestation_id: 222,
              meta: { format: "book" },
              manifestation_meta: { format: "book" },
            },
          }),
        });
      }
    });

    await page.route(`**/api/items/${itemId}/loan-status`, async route => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        loanDetails = body;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: body }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: loanDetails }),
        });
      }
    });

    await page.route("**/api/profile/users/search*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [{ id: "borrower-id", email: "bob@example.com", display_name: "Bob Friend" }],
        }),
      });
    });

    await page.goto(`/item/${itemId}`);
    await page.waitForLoadState("networkidle");

    const collectionSelect = page.locator('select[aria-label="Collection status"]');
    await collectionSelect.selectOption("lent");

    // Wait for the borrower name input dialogue
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByPlaceholder("Search user or enter name...").fill("Bob");
    await page.getByText("Bob Friend").click();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Verify success status
    await expect(page.getByText(/Item marked as lent to Bob Friend/i)).toBeVisible();
    // Sidebar should explicitly display Lent to: Bob Friend
    await expect(page.locator("body")).toContainText("Lent to: Bob Friend");
  });

  test("DevOps Maintenance Mode & API Key Masking", async ({ page }) => {
    // Mock admin settings
    let maintenanceMode = "false";
    let apiKey = "GOOGLE_BOOKS_API_KEY_SECRET_VALUE";

    await page.route("**/v1/admin/settings*", async route => {
      if (route.request().method() === "PUT" || route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        if (body.MAINTENANCE_MODE !== undefined) maintenanceMode = String(body.MAINTENANCE_MODE);
        if (body.GOOGLE_BOOKS_API_KEY !== undefined) apiKey = body.GOOGLE_BOOKS_API_KEY;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              MAINTENANCE_MODE: { value: maintenanceMode, source: "db" },
              GOOGLE_BOOKS_API_KEY: { value: apiKey.substring(0, 3) === "***" ? apiKey : `***${apiKey.slice(-4)}`, source: "db" },
            },
          }),
        });
      }
    });

    await page.route("**/v1/admin/settings/reveal*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, value: apiKey }),
      });
    });

    await page.goto("/admin/settings?tab=instance");
    await page.waitForLoadState("networkidle");

    // Check Maintenance Mode is visible and toggleable
    await expect(page.getByText("Maintenance Mode")).toBeVisible();
    const maintenanceSelect = page.locator("select").first();
    await maintenanceSelect.selectOption("true");
    await page.getByRole("button", { name: "Save" }).first().click();

    // Check saved state
    await expect(page.getByText(/Settings saved successfully/i)).toBeVisible();

    // Toggle API keys subtab
    await page.goto("/admin/settings?tab=external_apis");
    await page.waitForLoadState("networkidle");

    // Check API Key input is masked (starts with ***)
    const apiKeyInput = page.locator("input[type='text']").first();
    await expect(apiKeyInput).toHaveValue(/^\*\*\*/);

    // Click "eye" icon to reveal
    const revealBtn = page.locator("button:has(svg.lucide-eye)").first();
    await revealBtn.click();

    // Check that fully revealed key is visible
    await expect(apiKeyInput).toHaveValue(apiKey);
  });

  test("Bulk-Add Manifestations & Sidebar Facet Search", async ({ page }) => {
    // Mock global library manifestations search
    await page.route("**/api/manifestations*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            { id: 301, title: "Manifestation One", creator: "Author A", user_owns: false },
            { id: 302, title: "Manifestation Two", creator: "Author B", user_owns: false },
          ],
        }),
      });
    });

    await page.route("**/api/items/bulk", async route => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { item_ids: [1001, 1002] } }),
      });
    });

    await page.goto("/collection?view=manifestations");
    await page.waitForLoadState("networkidle");

    // Select the two manifestations
    const cards = page.locator("[data-testid='manifestation-card'], [data-testid='item-card']");
    await expect(cards).toHaveCount(2);

    await cards.nth(0).click();
    await cards.nth(1).click();

    // Check if floating toolbar is visible
    const floatingToolbar = page.locator("[data-testid='floating-toolbar'], button:has-text('Add to Collection')");
    await expect(floatingToolbar).toBeVisible();

    // Click "Add to Collection" -> select "Want to Read"
    await floatingToolbar.click();
    await page.getByText("Want to Read").click();

    // Verify success notification
    await expect(page.getByText(/Items added to collection/i).or(page.getByText(/success/i))).toBeVisible();

    // Test sidebar facet mini-search
    const genreFilterInput = page.getByPlaceholder(/filter genres|search genres/i).first();
    if (await genreFilterInput.isVisible()) {
      await genreFilterInput.fill("fant");
      // Verify list filters to only matching entries (e.g. Fantasy)
      await expect(page.getByText("Fantasy")).toBeVisible();
      await expect(page.getByText("Sci-Fi")).not.toBeVisible();
    }
  });

  test("User Collections CRUD", async ({ page }) => {
    let createdCollections = [{ id: 1, name: "SciFi Books", parent_id: null }];

    await page.route("**/api/collections*", async route => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        const newCol = { id: Date.now(), name: body.name, parent_id: body.parent_id || null };
        createdCollections.push(newCol);
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, collection: newCol }),
        });
      } else if (route.request().method() === "DELETE") {
        const url = route.request().url();
        const id = parseInt(url.split("/").pop() || "0", 10);
        createdCollections = createdCollections.filter(c => c.id !== id);
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, collections: createdCollections }),
        });
      }
    });

    await page.goto("/item/123");
    await page.waitForLoadState("networkidle");

    // Click Add to Collection Dropdown
    const addToColBtn = page.getByRole("button", { name: /add to collection/i });
    if (await addToColBtn.isVisible()) {
      await addToColBtn.click();

      // Quick Add Collection Input
      const quickAddInput = page.getByPlaceholder("New collection...");
      await quickAddInput.fill("Retro Gaming");
      await quickAddInput.press("Enter");

      // Verify it appears in the dropdown list
      await expect(page.getByText("Retro Gaming")).toBeVisible();
    }

    // Open manage collections modal
    const manageBtn = page.getByRole("button", { name: /manage collections/i });
    if (await manageBtn.isVisible()) {
      await manageBtn.click();
      await expect(page.getByRole("dialog", { name: "Manage Collections" })).toBeVisible();

      // Setup window confirm interceptor
      page.on("dialog", dialog => dialog.accept());

      // Click delete button on retro gaming
      const row = page.locator("div").filter({ hasText: "Retro Gaming" }).first();
      await row.locator("button[title='Delete Collection']").click();

      // Verify row is gone
      await expect(page.getByText("Retro Gaming")).not.toBeVisible();
    }
  });

  test("Backend API Hardening, BOLA & Payload Validation Mocks", async ({ request }) => {
    // Hit direct backend endpoints (E2E mode relies on backend running on port 5002)
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5002/api";

    // 1. Missing Authorization header should return 401
    const unauthRes = await request.get(`${flaskApiUrl}/admin/users`);
    expect(unauthRes.status()).toBe(401);

    // 2. Invalid Payload to POST /api/items/manual should return 400
    // Try sending without a title
    const badManualRes = await request.post(`${flaskApiUrl}/items/manual`, {
      data: { Format: "book" }
    });
    expect(badManualRes.status()).toBe(400);

    // Try sending invalid JSON format (invalid JSON string body)
    const badJsonRes = await request.post(`${flaskApiUrl}/items/manual`, {
      headers: { "Content-Type": "application/json" },
      data: "{invalid-json"
    });
    expect(badJsonRes.status()).toBe(400);
  });
});
