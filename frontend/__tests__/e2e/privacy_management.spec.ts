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
  test("private profile returns 404", async ({ page }) => {
    // This assumes 'privateuser' is private
    const response = await page.goto("/u/privateuser");
    expect(response?.status()).toBe(404);
  });

  test("hidden items are not visible in public grid", async ({ page }) => {
    // This requires specific setup where 'testuser' has 1 public and 1 hidden item
    await page.goto("/u/testuser");
    await expect(page.getByText("Hidden Treasure")).not.toBeVisible();
    await expect(page.getByText("Public Treasure")).toBeVisible();
  });
});
