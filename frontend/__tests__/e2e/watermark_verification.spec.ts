// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { test, expect } from "@playwright/test";

test.describe("Watermark Verification Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // Logowanie jako administrator
    await page.goto("/login");
    await page.fill('input[name="email"]', "admin@iqoqo.cc");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/dashboard");
  });

  test("verifies corner watermark presence on GenAI covers", async ({ page }) => {
    await page.goto("/admin/content");

    // Lokalizacja wygenerowanej okładki
    const genAiCover = page.locator('img[data-cover-type="llm_gen"]').first();
    await expect(genAiCover).toBeVisible();

    // Weryfikacja obecności sufiksu po przetworzeniu w tle
    const src = await genAiCover.getAttribute("src");
    expect(src).toContain("_wm.jpg");

    // Weryfikacja wizualna (wymaga wcześniejszego wygenerowania wzorców)
    // await expect(genAiCover).toHaveScreenshot('llm_gen_corner_wm.png', { maxDiffPixels: 100 });
  });

  test("verifies center watermark presence on placeholders", async ({ page }) => {
    await page.goto("/admin/content");

    // Lokalizacja okładki zastępczej (placeholder)
    const placeholderCover = page.locator('img[data-cover-type="placeholder"]').first();
    await expect(placeholderCover).toBeVisible();

    // Weryfikacja obecności sufiksu po przetworzeniu w tle
    const src = await placeholderCover.getAttribute("src");
    expect(src).toContain("_wm.jpg");

    // Weryfikacja wizualna (wymaga wcześniejszego wygenerowania wzorców)
    // await expect(placeholderCover).toHaveScreenshot('placeholder_center_wm.png', { maxDiffPixels: 100 });
  });
});
