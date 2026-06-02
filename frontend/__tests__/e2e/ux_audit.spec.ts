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
// frontend/__tests__/e2e/ux_audit.spec.ts
import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("UX/UI Audit Workflow", () => {
  // 1. Audit public landing page of dev.iqoqo.cc
  test("Audit dev.iqoqo.cc landing page button density and CTAs", async ({ page }) => {
    console.log("=== NAVIGATING TO DEV.IQOQO.CC ===");
    await page.goto("https://dev.iqoqo.cc", { timeout: 30000 });
    try {
      await page.waitForLoadState("networkidle", { timeout: 10000 });
    } catch {
      console.log("Timeout waiting for networkidle on external site, proceeding.");
    }

    // Take screenshot of landing page
    await page.screenshot({ path: "../.context/notes/images/ux_dev_landing.png", fullPage: true });
    console.log("dev.iqoqo.cc landing page screenshot saved to .context/notes/images/ux_dev_landing.png");

    // Count all buttons and anchor tags styled as buttons on the landing page
    const buttons = await page.locator("button, a[role='button'], a.btn").all();
    console.log(`[AUDIT] dev.iqoqo.cc landing page - total buttons: ${buttons.length}`);

    // Analyze visible elements and hierarchy
    let primaryCTAs = 0;
    for (const btn of buttons) {
      const text = (await btn.innerText()).trim();
      const isVisible = await btn.isVisible();
      if (isVisible) {
        console.log(`- Visible button text: "${text}"`);
        if (
          text.toLowerCase().includes("sign in") ||
          text.toLowerCase().includes("get started") ||
          text.toLowerCase().includes("try")
        ) {
          primaryCTAs++;
        }
      }
    }
    console.log(`[AUDIT] dev.iqoqo.cc landing page - primary CTAs: ${primaryCTAs}`);
  });

  // 2. Audit local dashboard (mocked authentication)
  test.describe("Authenticated UX Audit (Mocked Local Server)", () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript(() => {
        window.localStorage.setItem("iqoqo-cookie-consent", "true");
      });

      // Mock user authentication state (matching useProfile hook)
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "test-user-id",
              email: "test@example.com",
              display_name: "Test User",
              roles: ["admin"], // audit both user and admin view
              permissions: ["upload:cover", "write:metadata", "update:item"],
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

      // Mock items to show on the dashboard (to audit current context card buttons)
      await page.route("**/api/items?**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: [
              {
                id: 101,
                title: "Mocked Book on Shelf",
                authors: ["Author One"],
                status: "reading",
                collection_status: "available",
                is_owner: true,
                manifestation: { id: 201, title: "Mocked Book on Shelf", format: "book" },
              },
              {
                id: 102,
                title: "Mocked Vinyl in Wish List",
                authors: ["Artist Two"],
                status: "unread",
                collection_status: "wish_list",
                is_owner: true,
                manifestation: { id: 202, title: "Mocked Vinyl in Wish List", format: "vinyl" },
              },
            ],
            pagination: { page: 1, per_page: 10, total: 2, pages: 1 },
          },
        })
      );
    });

    test("Audit Dashboard button density and navigation actions", async ({ page }) => {
      await page.goto("/");
      await page.waitForLoadState("networkidle");

      // Capture screenshot of authenticated dashboard
      await page.screenshot({ path: "../.context/notes/images/ux_dashboard.png", fullPage: true });
      console.log("Dashboard screenshot saved to .context/notes/images/ux_dashboard.png");

      // Count buttons inside the sticky navbar
      const navbarButtons = await page.locator("nav button, nav a").all();
      console.log(`[AUDIT] Navbar - total interactive components: ${navbarButtons.length}`);
      for (const btn of navbarButtons) {
        const text = (await btn.innerText()).trim();
        const ariaLabel = await btn.getAttribute("aria-label");
        console.log(`  - Navbar action: "${text || ariaLabel || "Icon/Link"}"`);
      }

      // Count buttons inside the "Current Context" container
      const contextButtons = await page
        .locator("section[aria-label='Currently active items'] button, section[aria-label='Currently active items'] a")
        .all();
      console.log(`[AUDIT] Currently active items section - total actions: ${contextButtons.length}`);

      // Count buttons inside individual ItemCards
      const cardButtons = await page.locator("[data-testid='item-card'] button").all();
      console.log(`[AUDIT] ItemCard - total internal buttons: ${cardButtons.length}`);
    });

    test("Measure Friction in Item Addition Sequence (Friction Map)", async ({ page }) => {
      // Mock identifier lookup
      await page.route("**/api/lookup/9780134685991?format=book", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              type: "Book",
              title: "Test Book",
              authors: ["Author A"],
              format: "book",
              barcode: "9780134685991",
            },
          },
        })
      );

      // Mock Add to Collection
      await page.route("**/api/scan", route =>
        route.fulfill({
          status: 201,
          json: {
            success: true,
            data: { item_id: 123, manifestation_id: 456 },
          },
        })
      );

      // Mock item details page
      await page.route("**/api/items/123", async route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: 123,
              title: "Test Book",
              is_owner: true,
              manifestation: {
                id: 456,
                title: "Test Book",
                format: "book",
              },
            },
          },
        })
      );

      await page.goto("/scan");
      await page.waitForLoadState("networkidle");

      // Screenshot 1: Scan Page initial view
      await page.screenshot({ path: "../.context/notes/images/ux_scan_page.png" });
      console.log("Scan page initial screenshot saved");

      let clickCount = 0;

      // Click 1: Switch to Manual Search tab
      await page.getByRole("button", { name: "Manual Search" }).click();
      clickCount++;

      // Input 1: Fill the lookup field
      await page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…").fill("9780134685991");

      // Click 2: Click search icon button
      await page.locator("button:has(svg.lucide-search)").click();
      clickCount++;

      // Wait for success card to be visible
      await expect(page.getByText("Test Book")).toBeVisible();
      await page.screenshot({ path: "../.context/notes/images/ux_success_card.png" });
      console.log("Success card screenshot saved");

      // Click 3: Add to Collection
      await page.getByRole("button", { name: "Add to Library" }).click();
      clickCount++;

      // Verify success redirect
      await expect(page).toHaveURL(/.*\/item\?id=123/);
      console.log(`[AUDIT] Manual Search Lookup Flow: Clicks = ${clickCount}, Inputs = 1, Success Redirect reached.`);
    });

    test.describe("Mobile Size UX Audit", () => {
      test.use({
        viewport: { width: 375, height: 812 },
        hasTouch: true,
      });

      test("Audit mobile landing page & authenticated dashboard", async ({ page }) => {
        console.log("=== NAVIGATING TO MOBILE DASHBOARD ===");
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Take screenshot of mobile dashboard
        await page.screenshot({ path: "../.context/notes/images/ux_mobile_dashboard.png" });
        console.log("Mobile dashboard screenshot saved");

        // Verify mobile navbar: "Collection" and "Scan" search box behaviour
        const searchForm = page.locator("form input[placeholder='Search your collection...']");
        const isSearchVisible = await searchForm.isVisible();
        console.log(`[AUDIT] Mobile Navbar - Is search input visible? ${isSearchVisible}`);

        // Verify navigation options (is mobile menu or other trigger available?)
        const collectionLink = page.locator("nav").getByRole("link", { name: "Collection" });
        const isCollectionVisible = await collectionLink.isVisible();
        console.log(`[AUDIT] Mobile Navbar - Is Collection link visible? ${isCollectionVisible}`);
      });

      test("Audit mobile collection page & filter drawer layout", async ({ page }) => {
        // Mock items search endpoint to render correctly
        await page.route("**/api/items?**", route =>
          route.fulfill({
            status: 200,
            json: {
              success: true,
              data: [
                {
                  id: 101,
                  title: "Mobile Item 1",
                  authors: ["Author One"],
                  status: "reading",
                  collection_status: "available",
                  is_owner: true,
                  manifestation: { id: 201, title: "Mobile Item 1", format: "book" },
                },
              ],
              pagination: { page: 1, per_page: 10, total: 1, pages: 1 },
            },
          })
        );

        console.log("=== NAVIGATING TO MOBILE COLLECTION ===");
        await page.goto("/collection");
        await page.waitForLoadState("networkidle");

        // Take initial mobile collection page screenshot
        await page.screenshot({ path: "../.context/notes/images/ux_mobile_collection.png" });
        console.log("Mobile collection screenshot saved");

        // Locate and click the mobile filters trigger button
        const filterTrigger = page.locator("button.lg\\:hidden:has-text('Filters')");
        if (await filterTrigger.first().isVisible()) {
          await filterTrigger.first().click();
          await page.waitForTimeout(500); // Wait for transition
          await page.screenshot({ path: "../.context/notes/images/ux_mobile_filters.png" });
          console.log("Mobile filters drawer screenshot saved");

          // Verify that MobileFilterDrawer content is visible
          await expect(page.getByRole("dialog", { name: "Filter drawer" })).toBeVisible();

          // Count active buttons inside filter drawer
          const drawerButtons = await page.locator("[role='dialog'] button").all();
          console.log(`[AUDIT] Mobile Filter Drawer - Total buttons inside drawer: ${drawerButtons.length}`);
        } else {
          console.log("[AUDIT] Mobile Filters button not visible on viewport");
        }
      });

      test("Measure mobile scan viewfinder and bottom sheet layout", async ({ page }) => {
        console.log("=== NAVIGATING TO MOBILE SCAN PAGE ===");
        await page.goto("/scan");
        await page.waitForLoadState("networkidle");

        // Mobile scan page screenshot
        await page.screenshot({ path: "../.context/notes/images/ux_mobile_scan.png" });
        console.log("Mobile scan page screenshot saved");

        // Verify camera start button is visible
        const startCameraButton = page.getByTestId("start-camera-button");
        await expect(startCameraButton).toBeVisible();

        // Audit tab buttons in bottom sheet on mobile viewport
        const tabBarcode = page.getByTestId("scanner-tab-barcode");
        const tabCover = page.getByTestId("scanner-tab-cover");
        const tabManual = page.getByTestId("scanner-tab-manual");
        await expect(tabBarcode).toBeVisible();
        await expect(tabCover).toBeVisible();
        await expect(tabManual).toBeVisible();

        console.log("[AUDIT] Mobile Scanner - Bottom sheet tabs are fully visible and accessible.");
      });
    });
  });
});
