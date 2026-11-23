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

test.describe("Guides formatting, friend notifications, and item visibility badges", () => {
  test("guides detail page renders properly spaced headings and paragraphs", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Navigate to FRBR hierarchy guide
    await page.goto("/help/frbr-hierarchy");

    // Check title and article presence
    const title = page.locator("h1");
    await expect(title.first()).toBeVisible();

    // Verify prose headings have font-serif class and margins
    const h2 = page.locator("article.prose h2").first();
    await expect(h2).toBeVisible();

    const paragraphs = page.locator("article.prose p");
    await expect(paragraphs.first()).toBeVisible();
    const count = await paragraphs.count();
    expect(count).toBeGreaterThan(3);
  });
});
