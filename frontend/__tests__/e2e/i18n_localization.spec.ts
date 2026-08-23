// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Internationalization (i18n) & Localization", () => {
  test.beforeEach(async ({ page }) => {
    // Start at the homepage before each test
    await page.goto("/");
  });

  test("should load English as the default locale and verify base strings", async ({ page }) => {
    // Verify default English placeholders and labels
    await expect(page.getByPlaceholder("Search your collection...")).toBeVisible();
    await expect(page.getByRole("link", { name: "Collection" })).toBeVisible();
  });

  test("should toggle language to Polish, verify DOM updates, and check cookie persistence", async ({ page }) => {
    // 1. Open the language toggle dropdown
    const languageToggle = page.getByRole("button", { name: /toggle language/i });
    await expect(languageToggle).toBeVisible();
    await languageToggle.click();

    // 2. Select Polish from the dropdown menu
    const polishOption = page.getByRole("menuitem", { name: "Polski" });
    await expect(polishOption).toBeVisible();
    await polishOption.click();

    // 3. Verify the DOM has updated to the Polish translations
    // Note: Playwright automatically waits for network/hydration settling
    await expect(page.getByPlaceholder("Szukaj w swojej kolekcji...")).toBeVisible();
    await expect(page.getByRole("link", { name: "Kolekcja" })).toBeVisible();

    // 4. Verify the NEXT_LOCALE cookie was correctly set for persistence
    const cookies = await page.context().cookies();
    const localeCookie = cookies.find(c => c.name === "NEXT_LOCALE");

    expect(localeCookie).toBeDefined();
    expect(localeCookie?.value).toBe("pl");
    expect(localeCookie?.sameSite).toBe("Lax");
  });

  test("should seamlessly switch back and forth between locales", async ({ page }) => {
    // Switch to Polish
    await page.getByRole("button", { name: /toggle language/i }).click();
    await page.getByRole("menuitem", { name: "Polski" }).click();
    await expect(page.getByPlaceholder("Szukaj w swojej kolekcji...")).toBeVisible();

    // Switch back to English
    await page.getByRole("button", { name: /toggle language/i }).click();
    await page.getByRole("menuitem", { name: "English" }).click();

    // Verify English translations are restored
    await expect(page.getByPlaceholder("Search your collection...")).toBeVisible();
    await expect(page.getByRole("link", { name: "Collection" })).toBeVisible();

    // Verify cookie updated back to 'en'
    const cookies = await page.context().cookies();
    const localeCookie = cookies.find(c => c.name === "NEXT_LOCALE");
    expect(localeCookie?.value).toBe("en");
  });

  test("should translate scanner UI strings between English and Polish", async ({ page }) => {
    // The scanner page is full-screen and does not include the language toggle;
    // switch locale on the home page and then verify the translated scanner UI.
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    await page
      .context()
      .addCookies([{ name: "iqoqo_session", value: "mock-session-i18n-scanner", domain: "localhost", path: "/" }]);

    await page.route("**/api/profile**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "i18n-scanner-user-id",
            email: "i18n-scanner@iqoqo.local",
            display_name: "i18n Scanner User",
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

    // Verify default English scanner strings
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("scanner-tab-barcode")).toContainText("Barcode");
    await expect(page.getByTestId("scanner-tab-cover")).toContainText("Snap Cover");
    await expect(page.getByTestId("scanner-tab-manual")).toContainText("Manual Search");
    await page.getByTestId("scanner-tab-manual").click();
    await expect(page.getByPlaceholder("ISBN, UPC, Discogs ID, or Artist – Title…")).toBeVisible();

    // Switch to Polish from the home page
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /toggle language/i }).click();
    await page.getByRole("menuitem", { name: "Polski" }).click();
    await expect(page.getByPlaceholder("Szukaj w swojej kolekcji...")).toBeVisible();

    // Verify Polish scanner strings
    await page.goto("/scan");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("scanner-tab-barcode")).toContainText("Kod kreskowy");
    await expect(page.getByTestId("scanner-tab-cover")).toContainText("Zrób zdjęcie okładki");
    await expect(page.getByTestId("scanner-tab-manual")).toContainText("Wyszukiwanie ręczne");
    await page.getByTestId("scanner-tab-manual").click();
    await expect(page.getByPlaceholder("ISBN, UPC, identyfikator Discogs lub wykonawca – tytuł…")).toBeVisible();

    // Switch back to English and verify the scanner UI updates
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /toggle language/i }).click();
    await page.getByRole("menuitem", { name: "English" }).click();
    await expect(page.getByPlaceholder("Search your collection...")).toBeVisible();

    await page.goto("/scan");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("scanner-tab-barcode")).toContainText("Barcode");
    await expect(page.getByTestId("scanner-tab-cover")).toContainText("Snap Cover");
    await expect(page.getByTestId("scanner-tab-manual")).toContainText("Manual Search");
  });
});
