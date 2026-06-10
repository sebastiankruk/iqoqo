// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Lending Workflow", () => {
  test("can search for a user and lend an item", async ({ page }) => {
    // 0. Mock User Profile and Config
    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "test-user-id",
            email: "test@iqoqo.local",
            permissions: ["upload:cover", "update:item", "write:metadata"],
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

    // 1. Mock the lookup endpoint for manual entry
    const testBarcode = "999999999999";
    await page.route(`**/api/lookup/${testBarcode}?format=book`, async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            Title: "Lending Test Book",
            Format: "book",
            barcode: testBarcode,
            meta: {
              authors: ["Test Author"],
            },
            source: "Open Library",
          },
        }),
      });
    });

    // Mock user search
    await page.route("**/api/profile/users/search?q=Bob", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: "friend-id",
              email: "bob@example.com",
              display_name: "Bob Friend",
            },
          ],
        }),
      })
    );

    // 1.5 Mock the unified POST /scan endpoint
    await page.route("**/api/scan", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            item_id: 1,
            manifestation_id: 100,
            barcode: testBarcode,
            title: "Lending Test Book",
            message: "Successfully added to your collection",
          },
        }),
      });
    });

    // 1.6 Mock the target Item page to prevent timeout on redirect
    await page.route("**/api/items/1**", async route => {
      const url = route.request().url();
      if (url.endsWith("/logs")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: [] }),
        });
      }
      if (url.includes("/loan-status")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: null }),
        });
      }
      if (route.request().method() === "PUT") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: { id: 1 } }),
        });
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: 1,
            owner_id: "test-user-id",
            status: "read",
            collection_status: "available",
            title: "Lending Test Book",
            meta: { format: "book" },
            manifestation_meta: { format: "book" },
          },
        }),
      });
    });

    // 2. Navigate to Scanner page
    await page.goto("/scan");

    // 3. Switch to Manual Search tab
    await page.getByRole("button", { name: "Manual Search" }).click();

    // 4. Enter barcode
    const barcodeInput = page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…");
    await barcodeInput.fill(testBarcode);
    await barcodeInput.press("Enter");

    // 5. Verify metadata displayed
    await expect(page.getByText("Lending Test Book")).toBeVisible({ timeout: 5000 });

    // 6. Click Add to Collection
    await page.getByRole("button", { name: "Add to Library" }).click();

    // 7. Verify dynamic success message toast
    await expect(page.getByText(/"Lending Test Book" added to your library!/i)).toBeVisible();

    // 8. The application redirects to the newly created item
    await expect(page).toHaveURL(/.*\/item\/\d+/);

    // 9. Wait for the page to load
    await expect(page.getByText("Availability & Condition")).toBeVisible();

    // 10. Select "Lent Out" from the collection status dropdown
    const collectionStatusSelect = page.locator('select[aria-label="Collection status"]');
    await collectionStatusSelect.selectOption("lent");

    // 11. Verify the dialog appears
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Lent Out Item")).toBeVisible();

    // 12. Type "Bob" into the borrower name input to trigger search
    const borrowerInput = page.getByPlaceholder("Search user or enter name...");
    await borrowerInput.fill("Bob");

    // 13. Wait for the search results to appear and click "Bob Friend"
    const searchResult = page.getByText("Bob Friend");
    await expect(searchResult).toBeVisible();
    await searchResult.click();

    // 14. Verify the input is populated with the selected user's name
    await expect(borrowerInput).toHaveValue("Bob Friend");

    // 15. Submit the dialog
    await page.getByRole("button", { name: "Confirm" }).click();

    // 16. Verify the success toast appears
    await expect(page.getByText(/Item marked as lent to Bob Friend/i)).toBeVisible();
  });
});

test.describe("v0.7.0 Lending Tracking Lifecycle", () => {
  test("should execute full request, approval, and timeline logging loop between borrower and lender", async ({
    browser,
  }) => {
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    await fetch(`${flaskApiUrl.replace(/\/$/, "")}/lending/test/reset`, { method: "POST" });

    // 1. Create isolated context for Owner/Lender (User B)
    const lenderContext = await browser.newContext();
    const lenderPage = await lenderContext.newPage();
    await lenderPage.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    // Auto-dismiss any login-failure alerts so the test doesn't hang
    lenderPage.on("dialog", dialog => dialog.dismiss());

    await lenderPage.goto("/login");
    await lenderPage.waitForLoadState("networkidle");
    await lenderPage.fill('input[type="email"]', "lender@iqoqo.local");
    await lenderPage.fill('input[type="password"]', "SecurePassword123!");
    await Promise.all([expect(lenderPage).toHaveURL(/\/(collection)?$/), lenderPage.click('button[type="submit"]')]);

    // 2. Create isolated context for Borrower (User A)
    const borrowerContext = await browser.newContext();
    const borrowerPage = await borrowerContext.newPage();
    await borrowerPage.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    // Auto-dismiss any login-failure alerts so the test doesn't hang
    borrowerPage.on("dialog", dialog => dialog.dismiss());

    await borrowerPage.goto("/login");
    await borrowerPage.waitForLoadState("networkidle");
    await borrowerPage.fill('input[type="email"]', "borrower@iqoqo.local");
    await borrowerPage.fill('input[type="password"]', "SecurePassword123!");
    await Promise.all([
      expect(borrowerPage).toHaveURL(/\/(collection)?$/),
      borrowerPage.click('button[type="submit"]'),
    ]);

    // 3. Borrower finds Lender's copy and requests a loan
    await borrowerPage.goto("/u/lender");
    const targetItem = borrowerPage.locator('[data-testid="item-card"]', { hasText: "Lendable Book" });
    const itemId = await targetItem.getAttribute("data-item-id");

    await targetItem.click();
    await expect(borrowerPage).toHaveURL(new RegExp(`/item/${itemId}`));

    const requestButton = borrowerPage.locator('button:has-text("Request Loan")');
    await expect(requestButton).toBeVisible();
    await requestButton.click();

    // Validate optimistic UI or pending request status banner
    await expect(borrowerPage.locator('[data-testid="loan-status-badge"]')).toHaveText("Pending Approval");

    // 4. Switch back to Lender to approve the pending request
    await lenderPage.goto("/admin/lending");
    const pendingRequestRow = lenderPage.locator(`[data-testid="request-row-${itemId}"]`);
    await expect(pendingRequestRow).toBeVisible();

    const approveButton = pendingRequestRow.locator('button[aria-label="Approve Loan"]');
    await approveButton.click();
    await expect(pendingRequestRow.locator('[data-testid="status-cell"]')).toHaveText("Lent");

    // 5. Verify Borrower's side automatically synchronizes and updates the FRBR timeline log
    await borrowerPage.goto(`/item/${itemId}`);
    await expect(borrowerPage).toHaveURL(`/item/${itemId}`);
    await borrowerPage.waitForLoadState("networkidle");
    // Ensure borrower sees the "On Loan" badge
    await expect(borrowerPage.locator('[data-testid="loan-status-badge"]')).toHaveText("On Loan");

    // Validate Event-Based Timeline Entry
    await borrowerPage.getByRole("button", { name: "History" }).click();
    const timelineContainer = borrowerPage.locator('[data-testid="frbr-timeline-log"]');
    await expect(timelineContainer).toBeVisible();
    await expect(timelineContainer.locator(".timeline-event").first()).toContainText("Loan approved by custodian");

    // Cleanup contexts cleanly
    await borrowerContext.close();
    await lenderContext.close();
  });
});
