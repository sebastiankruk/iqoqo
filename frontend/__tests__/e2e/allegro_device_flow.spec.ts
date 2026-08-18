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
// frontend/__tests__/e2e/allegro_device_flow.spec.ts

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

/**
 * Mock fixtures matching Allegro OAuth Device Authorization Grant contract (RFC 8628).
 * Reference: https://developer.allegro.pl/tutorials/jak-uwierzytelnic-sie-w-allegro-api-device-code-flow
 */
const MOCK_DEVICE_FLOW_INIT_RESPONSE = {
  device_code: "d9a8f2e1-mock-device-code",
  user_code: "E2E-ALLEGRO-99",
  verification_uri: "https://allegro.pl/auth/device",
  verification_uri_complete: "https://allegro.pl/auth/device?user_code=E2E-ALLEGRO-99",
  expires_in: 600,
  interval: 1,
};

const MOCK_DEVICE_TOKEN_PENDING_RESPONSE = {
  status: "pending",
  error: "authorization_pending",
  error_description: "The authorization request is still pending as the end-user hasn't yet completed the flow.",
};

const MOCK_DEVICE_TOKEN_SUCCESS_RESPONSE = {
  status: "success",
  message: "Allegro authorized successfully",
};

const MOCK_DEVICE_TOKEN_DENIED_RESPONSE = {
  error: "access_denied",
  error_description: "The end-user denied the authorization request.",
};

test.describe("Allegro OAuth Device Flow E2E Contract Tests", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Consent to cookies
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // 2. Mock app config endpoint
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

    // 3. Prevent external browser popup windows during tests
    await page.addInitScript(() => {
      window.open = () => null;
    });

    // 4. Admin login
    const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000/api";
    const loginRes = await page.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "e2e-admin@iqoqo.local", password: "E2ETestPassword123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { token } = await loginRes.json();
    await page.goto(`/api/auth-exchange?token=${token}`);
    await page.waitForURL(/\/(collection)?$/);
  });

  test("Happy Path: Admin initiates device flow, views code/link, and successfully polls token", async ({ page }) => {
    let pollCount = 0;

    // Intercept device flow initiation
    await page.route("**/api/auth/allegro/device-flow", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DEVICE_FLOW_INIT_RESPONSE),
      });
    });

    // Intercept polling: return 202 once, then 200 success
    await page.route("**/api/auth/allegro/device-token", async route => {
      pollCount++;
      if (pollCount === 1) {
        await route.fulfill({
          status: 202,
          contentType: "application/json",
          body: JSON.stringify(MOCK_DEVICE_TOKEN_PENDING_RESPONSE),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_DEVICE_TOKEN_SUCCESS_RESPONSE),
        });
      }
    });

    // Navigate to Admin Settings -> External APIs
    await page.goto("/admin/settings?tab=apikeys");
    await page.waitForLoadState("networkidle");

    // Locate and click the Authorize Allegro Account button
    const authButton = page.getByRole("button", { name: /Authorize Allegro Account/i });
    await expect(authButton).toBeVisible();
    await authButton.click();

    // Verify user code and pending status are rendered
    await expect(page.getByText(/Authorize code: E2E-ALLEGRO-99/i)).toBeVisible();
    await expect(page.getByText(/Waiting for confirmation/i)).toBeVisible();

    // Verify verification URL link is displayed
    const verificationLink = page.getByRole("link", { name: /click here to authorize on Allegro/i });
    await expect(verificationLink).toBeVisible();
    await expect(verificationLink).toHaveAttribute("href", "https://allegro.pl/auth/device?user_code=E2E-ALLEGRO-99");

    // Verify success confirmation appears after polling resolves
    await expect(page.getByText(/Allegro authorized successfully!/i)).toBeVisible({ timeout: 10000 });
  });

  test("Error Path: Device flow initiation network error displays error without polling loop", async ({ page }) => {
    let tokenPollCalled = false;

    // Intercept initiation with 500 error
    await page.route("**/api/auth/allegro/device-flow", async route => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Failed to initiate device flow" }),
      });
    });

    await page.route("**/api/auth/allegro/device-token", async route => {
      tokenPollCalled = true;
      await route.fulfill({ status: 500 });
    });

    await page.goto("/admin/settings?tab=apikeys");
    await page.waitForLoadState("networkidle");

    const authButton = page.getByRole("button", { name: /Authorize Allegro Account/i });
    await expect(authButton).toBeVisible();
    await authButton.click();

    // Verify error message is shown in UI
    await expect(page.getByText(/Error: Failed to initiate device flow/i)).toBeVisible();

    // Verify button is re-enabled and polling never triggered
    await expect(authButton).toBeEnabled();
    expect(tokenPollCalled).toBe(false);
  });

  test("Error Path: Allegro returns 401 / access denied during polling", async ({ page }) => {
    await page.route("**/api/auth/allegro/device-flow", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DEVICE_FLOW_INIT_RESPONSE),
      });
    });

    // Intercept token poll with 400 access denied / failure
    await page.route("**/api/auth/allegro/device-token", async route => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DEVICE_TOKEN_DENIED_RESPONSE),
      });
    });

    await page.goto("/admin/settings?tab=apikeys");
    await page.waitForLoadState("networkidle");

    const authButton = page.getByRole("button", { name: /Authorize Allegro Account/i });
    await expect(authButton).toBeVisible();
    await authButton.click();

    // Verify failure notification is shown
    await expect(page.getByText(/Authorization failed or denied/i)).toBeVisible({ timeout: 10000 });
  });

  test("Error Path: Device code expires during polling", async ({ page }) => {
    // Initiate with very short expiration (1 second) and 1s interval
    await page.route("**/api/auth/allegro/device-flow", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...MOCK_DEVICE_FLOW_INIT_RESPONSE,
          interval: 1,
          expires_in: 1,
        }),
      });
    });

    // Return 202 pending so timer decrements expires_in to 0
    await page.route("**/api/auth/allegro/device-token", async route => {
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DEVICE_TOKEN_PENDING_RESPONSE),
      });
    });

    await page.goto("/admin/settings?tab=apikeys");
    await page.waitForLoadState("networkidle");

    const authButton = page.getByRole("button", { name: /Authorize Allegro Account/i });
    await expect(authButton).toBeVisible();
    await authButton.click();

    // Verify expiration message appears and button is re-enabled
    await expect(page.getByText(/Authorization expired. Please try again./i)).toBeVisible({ timeout: 10000 });
    await expect(authButton).toBeEnabled();
  });
});
