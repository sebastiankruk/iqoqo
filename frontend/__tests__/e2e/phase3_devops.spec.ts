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

test.describe("Phase 3 DevOps & UI Features", () => {
  test("Landing page has functional GitHub link", async ({ page }) => {
    await page.goto("/");
    const githubLink = page.locator('a:has-text("GitHub")');
    await expect(githubLink).toBeVisible();
    await expect(githubLink).toHaveAttribute("href", "https://github.com/sebastiankruk/iqoqo");
    await expect(githubLink).toHaveAttribute("target", "_blank");
  });

  test("Admin internal settings show Maintenance Mode toggle", async ({ page }) => {
    // Note: This requires admin login which is typically handled in global setup or via a helper
    // For this E2E test we assume the session is available or we bypass auth for the check
    // In a real run, we'd use: await loginAsAdmin(page);
    await page.goto("/admin/settings?tab=internal");
    
    // Check if the Maintenance Mode card exists
    await expect(page.locator("text=Maintenance Mode")).toBeVisible();
    await expect(page.locator("select")).toBeVisible();
  });
});
