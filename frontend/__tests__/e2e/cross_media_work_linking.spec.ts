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

import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "ci-admin@iqoqo.cc";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "E2EBootstrapPassword123!";

test.describe("Cross-Media FRBR Work Linking (C144)", () => {
  test("custodian can visit /admin/work-links and toggle derivatives on /graph", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"], input[name="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"], input[name="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(url => !url.pathname.includes("/login"), { timeout: 15000 });

    await page.goto("/admin/work-links");
    await expect(page.getByRole("heading", { name: /cross-media work links/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /scan for cross-media links/i })).toBeVisible();

    await page.goto("/graph");
    await expect(page.getByRole("button", { name: /derivatives & adaptations/i })).toBeVisible();
  });
});
