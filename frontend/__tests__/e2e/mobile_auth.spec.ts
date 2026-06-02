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
// frontend/__tests__/e2e/mobile_auth.spec.ts
//
// E2E tests for the mobile authentication flow.
// Simulates the Capacitor WebView experience using Playwright's mobile
// device emulation (Pixel 7 viewport). Tests the web content that runs
// inside the WebView — Capacitor plugin calls (secure storage, deep links)
// are covered by Vitest unit tests.

import { test, expect } from "@playwright/test";

test.describe("Mobile Authentication Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Dismiss cookie consent
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
  });

  test.describe("Login Page", () => {
    test("renders login form with Google button on mobile viewport", async ({ page }) => {
      await page.goto("/login");

      // Title
      await expect(page.getByRole("heading", { name: "Sign in to iqoqo" })).toBeVisible();

      // Google button
      await expect(page.getByRole("button", { name: /sign in with google/i })).toBeVisible();

      // Email/password fields
      await expect(page.getByPlaceholder("Email")).toBeVisible();
      await expect(page.getByPlaceholder("Password")).toBeVisible();

      // Sign In button
      await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
    });

    test("shows registration link", async ({ page }) => {
      await page.goto("/login");

      const signUpLink = page.getByRole("link", { name: "Sign up" });
      await expect(signUpLink).toBeVisible();
      await expect(signUpLink).toHaveAttribute("href", "/register");
    });
  });

  test.describe("Local Email Login", () => {
    test("successful local login redirects to auth-exchange", async ({ page }) => {
      // Mock the local login API endpoint
      await page.route("**/api/auth/login", route =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: "test-jwt-token-local",
            user: { id: "user-1", email: "test@example.com" },
          }),
        })
      );

      // Mock the auth-exchange page to succeed (when navigating to it)
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-1",
              email: "test@example.com",
              display_name: "Test User",
              roles: ["user"],
              permissions: [],
            },
          },
        })
      );

      await page.route("**/api/config**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { federation_enabled: false, version: "0.8.0" },
          },
        })
      );

      await page.goto("/login");

      // Fill the form
      await page.getByPlaceholder("Email").fill("test@example.com");
      await page.getByPlaceholder("Password").fill("securepassword");

      // Submit
      await page.getByRole("button", { name: "Sign In" }).click();

      // Should navigate to auth-exchange with token
      await expect(page).toHaveURL(/auth-exchange\?token=test-jwt-token-local/);
    });

    test("failed login shows alert", async ({ page }) => {
      // Mock failed login
      await page.route("**/api/auth/login", route =>
        route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ error: "Invalid credentials" }),
        })
      );

      // Intercept the alert dialog
      page.on("dialog", dialog => dialog.accept());

      await page.goto("/login");
      await page.getByPlaceholder("Email").fill("wrong@example.com");
      await page.getByPlaceholder("Password").fill("wrongpassword");
      await page.getByRole("button", { name: "Sign In" }).click();

      // Should stay on login page
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("Auth Exchange Page", () => {
    test("with valid token, redirects to dashboard", async ({ page }) => {
      // Mock profile API (called after auth exchange sets token)
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: "user-1",
              email: "test@example.com",
              display_name: "Test User",
              roles: ["user"],
              permissions: [],
            },
          },
        })
      );

      await page.route("**/api/config**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { federation_enabled: false, version: "0.8.0" },
          },
        })
      );

      // Mock the BFF auth-exchange route (web mode — sets httpOnly cookie)
      await page.route("**/api/auth-exchange**", route =>
        route.fulfill({
          status: 200,
          headers: {
            "Set-Cookie": "iqoqo_session=test-jwt-token; Path=/; HttpOnly",
          },
          body: "",
        })
      );

      // Mock the items/dashboard data
      await page.route("**/api/items**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { items: [], total: 0, page: 1, pages: 1 },
          },
        })
      );

      await page.goto("/auth-exchange?token=test-jwt-token");

      // Should redirect to the home page
      await page.waitForURL("**/", { timeout: 10000 });
    });

    test("without token, redirects to login", async ({ page }) => {
      await page.goto("/auth-exchange");

      // Should redirect to login page
      await page.waitForURL("**/login", { timeout: 10000 });
    });
  });

  test.describe("Google OAuth Flow", () => {
    test("Google login button triggers backend redirect", async ({ page }) => {
      // Track navigation to the Google login endpoint
      let googleLoginUrl = "";

      page.on("request", request => {
        if (request.url().includes("/api/auth/login/google")) {
          googleLoginUrl = request.url();
        }
      });

      // Mock the Google login redirect (prevent actual OAuth flow)
      await page.route("**/api/auth/login/google**", route =>
        route.fulfill({
          status: 302,
          headers: {
            Location: "https://accounts.google.com/o/oauth2/auth?client_id=fake",
          },
        })
      );

      await page.goto("/login");
      await page.getByRole("button", { name: /sign in with google/i }).click();

      // Verify the request was made to the backend
      expect(googleLoginUrl).toContain("/api/auth/login/google");
    });
  });

  test.describe("Protected Route Access", () => {
    test("unauthenticated user sees login when accessing scan page", async ({ page }) => {
      // Mock profile as unauthenticated
      await page.route("**/api/profile**", route =>
        route.fulfill({
          status: 401,
          json: { error: "Token missing" },
        })
      );

      await page.route("**/api/config**", route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { federation_enabled: false, version: "0.8.0" },
          },
        })
      );

      await page.goto("/scan");

      // Should show the login/auth prompt (navbar shows login link)
      await expect(page.getByRole("link", { name: /sign in|log in/i })).toBeVisible({
        timeout: 10000,
      });
    });
  });
});
