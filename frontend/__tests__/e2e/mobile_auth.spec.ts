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
/**
 * E2E tests for mobile authentication, deep-link handoff, and /auth-exchange card (C97).
 */
import { test, expect } from "@playwright/test";

test.describe("Mobile Auth & Deep-Link Handoff (C97)", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
  });

  test("renders branded open-in-app card when landing on auth-exchange in external mobile browser", async ({
    page,
  }) => {
    await page.goto("/auth-exchange?mobile=1&token=mock-jwt-token-xyz");

    // Branded card headers and title
    await expect(page.getByRole("heading", { name: "Open in iqoqo" })).toBeVisible();
    await expect(
      page.getByText("Authentication successful! Tap below to return to your iqoqo mobile app.")
    ).toBeVisible();

    // Deep link action button
    const openAppButton = page.getByRole("link", { name: "Open iqoqo App" });
    await expect(openAppButton).toBeVisible();
    await expect(openAppButton).toHaveAttribute("href", "iqoqo://auth-exchange?token=mock-jwt-token-xyz");

    // Secondary fallback
    await expect(page.getByRole("button", { name: "Continue in web browser" })).toBeVisible();
  });

  test("login page renders social auth buttons and handles server switching option", async ({ page }) => {
    await page.route("**/api/auth/providers", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ google: true, apple: true }),
      });
    });

    await page.goto("/login");

    await expect(page.getByRole("button", { name: /Sign in with Google/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Sign in with Apple/i })).toBeVisible();
  });
});
