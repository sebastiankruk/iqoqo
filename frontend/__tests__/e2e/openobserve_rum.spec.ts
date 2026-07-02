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

import { test, expect } from "@playwright/test";

test.describe("OpenObserve RUM Integration", () => {
  test("OpenObserve RUM should initialize successfully on the client side", async ({ page }) => {
    // Navigate to landing page
    await page.goto("/");

    // Wait for our global initialization flag to be set to true (since SDKs load dynamically)
    await page.waitForFunction(() => {
      return (window as any).__OPENOBSERVE_RUM_INITIALIZED__ === true;
    }, { timeout: 10000 });

    const isInitialized = await page.evaluate(() => {
      return (window as any).__OPENOBSERVE_RUM_INITIALIZED__ === true;
    });

    expect(isInitialized).toBe(true);
  });
});
