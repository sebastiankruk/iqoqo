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

test.describe("Help Hub Workflow & Bilingual Documentation", () => {
  test.beforeEach(async ({ page }) => {
    // Set cookie consent bypass
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
  });

  test("navigates to /help, explores guide categories, and reads an article", async ({ page }) => {
    await page.goto("/help");

    // 1. Verify Help Hub header and search bar
    await expect(page.getByRole("heading", { level: 1, name: "Help & Guides" })).toBeVisible();
    const searchInput = page.getByPlaceholder("Search documentation articles...");
    await expect(searchInput).toBeVisible();

    // 2. Verify category filters are rendered
    await expect(page.getByRole("button", { name: "All Guides" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cataloging & FRBR" })).toBeVisible();

    // 3. Search for FRBR article
    await searchInput.fill("Dune");
    await expect(page.getByRole("link", { name: /Beyond the Bookshelf/i })).toBeVisible();

    // 4. Clear search and click the FRBR hierarchy guide card
    await searchInput.clear();
    const articleLink = page.getByRole("link", { name: /Beyond the Bookshelf/i });
    await expect(articleLink).toBeVisible();
    await articleLink.click();

    // 5. Verify detail page content at /help/frbr-hierarchy
    await expect(page).toHaveURL(/\/help\/frbr-hierarchy/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Beyond the Bookshelf: How iqoqo Organizes Your World" })
    ).toBeVisible();
    await expect(page.getByText("The Four Pillars of FRBR")).toBeVisible();

    // 6. Navigate back to Help Hub using breadcrumb / back button
    const backButton = page.getByRole("link", { name: /Back to Help & Guides/i });
    await expect(backButton).toBeVisible();
    await backButton.click();
    await expect(page).toHaveURL(/\/help$/);
  });

  test("switches between English and Polish locales on Help Hub and article page", async ({ page }) => {
    await page.goto("/help");

    // Initially in English
    await expect(page.getByRole("heading", { level: 1, name: "Help & Guides" })).toBeVisible();

    // Toggle language to Polish
    const languageToggle = page.getByRole("button", { name: /toggle language/i });
    await expect(languageToggle).toBeVisible();
    await languageToggle.click();

    const polishOption = page.getByRole("menuitem", { name: "Polski" });
    await expect(polishOption).toBeVisible();
    await polishOption.click();

    // Verify Polish translation updates on Help Hub
    await expect(page.getByRole("heading", { level: 1, name: "Pomoc i poradniki" })).toBeVisible();
    await expect(page.getByPlaceholder("Szukaj w poradnikach...")).toBeVisible();
    await expect(page.getByRole("link", { name: /Więcej niż półka z książkami/i })).toBeVisible();

    // Click into Polish article
    await page.getByRole("link", { name: /Więcej niż półka z książkami/i }).click();
    await expect(page).toHaveURL(/\/help\/frbr-hierarchy/);
    await expect(page.getByRole("heading", { level: 1, name: /Więcej niż półka z książkami/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Powrót do pomocy i poradników/i })).toBeVisible();

    // Switch back to English while on article page
    await page.getByRole("button", { name: /toggle language/i }).click();
    await page.getByRole("menuitem", { name: "English" }).click();

    await expect(page.getByRole("heading", { level: 1, name: /Beyond the Bookshelf/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Back to Help & Guides/i })).toBeVisible();
  });
});
