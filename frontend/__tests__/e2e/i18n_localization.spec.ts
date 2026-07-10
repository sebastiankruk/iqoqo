// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
import { test, expect } from "@playwright/test";

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
});
