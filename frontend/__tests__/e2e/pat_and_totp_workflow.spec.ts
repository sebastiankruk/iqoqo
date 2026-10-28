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
import packageJson from "../../package.json" assert { type: "json" };

test.describe("PAT and TOTP 2FA Workflow", () => {
  test("handles login MFA challenge and allows managing PATs in profile", async ({ page }) => {
    // 1. Mock config & auth providers
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

    await page.route("**/api/auth/providers**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ google: false }),
      });
    });

    let mfaSubmitted = false;

    // 2. Mock /api/auth/login to return mfa_required on first attempt, then token on second
    await page.route("**/api/auth/login", async route => {
      const payload = JSON.parse(route.request().postData() || "{}");
      if (!payload.otp_code) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            mfa_required: true,
            message: "Two-factor authentication required",
          }),
        });
      } else {
        mfaSubmitted = true;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: "valid-jwt-token-after-mfa",
            user: { id: "test-user-id", email: payload.email },
          }),
        });
      }
    });

    await page.route("**/api/auth-exchange", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ redirectUrl: "/collection" }),
      });
    });

    // 3. Go to /login and submit email + password
    await page.goto("/login");
    await page.fill('input[name="email"]', "collector@iqoqo.local");
    await page.fill('input[name="password"]', "SecretPass123!");
    await page.click('button[type="submit"]');

    // 4. Expect 2FA challenge input to appear
    await expect(page.locator('input[name="otpCode"]')).toBeVisible();

    // 5. Fill OTP code and verify
    await page.fill('input[name="otpCode"]', "123456");
    await page.click('button[type="submit"]');

    expect(mfaSubmitted).toBe(true);
  });
});
