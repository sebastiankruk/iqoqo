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

    // 1b. Login via direct Flask API call (avoids Next.js proxy POST body issues)
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = await loginRes.json();
    await page.goto(`/api/auth-exchange?token=${token}`);
    await page.waitForURL(/\/(collection|dashboard|profile|admin)?$/);

    // 2. Mock default profile endpoint (real login step above already provides iqoqo_session cookie)
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
    await expect(page.getByText(/Username already taken/i).first()).toBeVisible();
  });

  test("Item-Level Privacy (is_hidden toggle)", async ({ page }) => {
    let itemState: any = null;

    // Intercept GET and PUT requests to track visibility in memory
    await page.route(/\/api\/items\/\d+/, async route => {
      if (route.request().method() === "PUT") {
        const body = route.request().postDataJSON();
        itemState = { ...itemState, ...body };
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: itemState }),
        });
      } else {
        if (!itemState) {
          const response = await route.fetch();
          const json = await response.json();
          itemState = json.data;
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: itemState }),
        });
      }
    });

    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    const firstCard = page.locator("[data-testid='item-card']").first();
    await expect(firstCard).toBeVisible();
    await firstCard.click();

    // Verify page has loaded
    await page.waitForURL(/\/item\/\d+$/);

    // Toggle the hidden setting
    const visibilityBtn = page.getByRole("button", { name: /hide from public|make public/i });
    await expect(visibilityBtn).toBeVisible();
    await visibilityBtn.click();
    await expect(page.getByText(/item is now hidden/i)).toBeVisible();
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

    await page.goto("/collection?statuses=want_to_read");
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
    let loanDetails: any = null;

    let itemState: any = null;

    // Mock GET and PUT requests to item status updates to track in memory
    await page.route(/\/api\/items\/\d+/, async route => {
      if (route.request().method() === "PUT") {
        const body = route.request().postDataJSON();
        itemState = { ...itemState, ...body };
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: itemState }),
        });
      } else {
        if (!itemState) {
          const response = await route.fetch();
          const json = await response.json();
          itemState = json.data;
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: itemState }),
        });
      }
    });

    await page.route(/\/api\/items\/\d+\/loan-status$/, async route => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        loanDetails = body;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: body }),
        });
      } else {
        await route.fulfill({
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

    await page.goto("/collection");
    await page.waitForLoadState("networkidle");

    const firstCard = page.locator("[data-testid='item-card']").first();
    await expect(firstCard).toBeVisible();
    await firstCard.click();

    // Verify page has loaded
    await page.waitForURL(/\/item\/\d+$/);

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
          body: JSON.stringify({ success: true, data: body }),
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              MAINTENANCE_MODE: { value: maintenanceMode, source: "db" },
              GOOGLE_BOOKS_API_KEY: {
                value: apiKey.substring(0, 3) === "***" ? apiKey : `***${apiKey.slice(-4)}`,
                source: "db",
              },
            },
          }),
        });
      }
    });

    await page.route("**/v1/admin/settings/reveal*", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { value: apiKey } }),
      });
    });

    await page.goto("/admin/settings?tab=instance");
    await page.waitForLoadState("networkidle");

    // Check Maintenance Mode is visible and toggleable
    await expect(page.getByText("Maintenance Mode")).toBeVisible();
    const maintenanceSelect = page.locator("select").first();
    await maintenanceSelect.selectOption("true");
    await page.getByRole("button", { name: "Save Changes" }).first().click();

    // Check saved state
    await expect(page.getByText(/Saved settings for/i)).toBeVisible();

    await page.goto("/admin/settings?tab=apikeys");
    await page.waitForLoadState("networkidle");

    // Check API Key input is masked (starts with ***)
    // Anchor on the field label and scope to its direct parent (the field
    // wrapper), which contains exactly one input and one reveal button.
    const apiKeyField = page.locator("label", { hasText: "Google Books API Key" }).locator("xpath=..");
    const apiKeyInput = apiKeyField.locator("input");
    await expect(apiKeyInput).toHaveValue(/^\*\*\*/);

    // Click "eye" icon to reveal
    const revealBtn = apiKeyField.locator("button");
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

    // Select the two manifestations by clicking the select overlay buttons
    await page.getByRole("button", { name: "Select" }).nth(0).click();
    await page.getByRole("button", { name: "Select" }).nth(1).click();

    // Check if floating toolbar is visible
    const floatingToolbar = page.locator("[data-testid='floating-toolbar'], button:has-text('Add to Collection')");
    await expect(floatingToolbar).toBeVisible();

    // Click "Add to Collection" -> select "Want to Read"
    await floatingToolbar.click();
    await page.getByText("Want to Read").click();

    // Verify success notification
    await expect(page.getByText(/Added 2 items/i)).toBeVisible();

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

  test("Backend API Hardening, BOLA & Payload Validation Mocks", async ({ page, request }) => {
    // Hit direct backend endpoints (E2E mode relies on backend running on port 5002)
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5002/api";

    // Get cookies from page context to authenticate backend API calls
    const cookies = await page.context().cookies();
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join("; ");

    // 1. Missing Authorization header should return 401
    const unauthRes = await request.get(`${flaskApiUrl}/v1/admin/users`);
    expect(unauthRes.status()).toBe(401);

    // 2. Invalid Payload to POST /api/items/manual should return 400
    // Try sending without a title
    const badManualRes = await request.post(`${flaskApiUrl}/items/manual`, {
      headers: { Cookie: cookieHeader },
      data: { Format: "book" },
    });
    expect(badManualRes.status()).toBe(400);

    // Try sending invalid JSON format (invalid JSON string body)
    const badJsonRes = await request.post(`${flaskApiUrl}/items/manual`, {
      headers: {
        "Content-Type": "application/json",
        Cookie: cookieHeader,
      },
      data: "{invalid-json",
    });
    expect(badJsonRes.status()).toBe(400);
  });
});
