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

test.describe("Privacy Management", () => {
  test("private profile shows 404 page", async ({ page }) => {
    // This assumes 'privateuser' is private (or user doesn't exist)
    await page.goto("/u/privateuser");
    // Next.js App Router always returns HTTP 200 for matching routes;
    // the notFound() call renders the 404 page client-side.
    await expect(page.getByRole("heading", { name: "This page could not be found." })).toBeVisible();
  });

  test("hidden items are not visible in public grid", async ({ page }) => {
    // This requires specific setup where 'testuser' has 1 public and 1 hidden item
    await page.goto("/u/testuser");
    await expect(page.getByText("Hidden Treasure")).not.toBeVisible();
    await expect(page.getByText("Public Treasure").first()).toBeVisible();
  });
});
