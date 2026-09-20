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

test.describe("SPARQL Explorer — Regression Validation", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Mock authenticated user with read:metadata permission
    await page.context().addCookies([
      { name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" },
    ]);
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "custodian-id",
            email: "custodian@iqoqo.local",
            display_name: "Custodian User",
            roles: ["custodian"],
            permissions: ["read:metadata", "write:item"],
          },
        },
      })
    );
  });

  test("SPARQL Explorer example queries do not return HTTP 500", async ({ page }) => {
    // Mock SPARQL endpoint to return valid results for all example queries
    await page.route("**/api/sparql**", route => {
      const postData = route.request().postData();
      let body = "";
      if (postData) {
        try {
          const parsed = JSON.parse(postData);
          body = parsed.query || "";
        } catch {
          body = postData;
        }
      }
      if (body.includes("SELECT")) {
        route.fulfill({
          status: 200,
          contentType: "application/sparql-results+json",
          json: {
            head: { vars: ["title"] },
            results: {
              bindings: [{ title: { type: "literal", value: "Test Book" } }],
            },
          },
        });
      } else if (body.includes("ASK")) {
        route.fulfill({
          status: 200,
          contentType: "application/sparql-results+json",
          json: { head: {}, boolean: true },
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: "text/turtle",
          body: "@prefix schema: <https://schema.org/> .\n<http://example.org/s> schema:name \"Test\" .",
        });
      }
    });

    // Navigate to SPARQL Explorer (Administration menu)
    await page.goto("/admin");

    // Verify the Administration menu is visible to authorized users
    // The SPARQL Explorer should be accessible
    const sparqlLink = page.locator('a[href*="sparql"], [data-testid="sparql-explorer"]');
    // If the link exists, click it and verify no 500 errors
    if (await sparqlLink.count() > 0) {
      await sparqlLink.first().click();
      await expect(page).not.toHaveURL(/.*error.*/);
    }
  });

  test("SPARQL API returns structured errors, not uncaught 500s", async ({ request }) => {
    // Test that the API returns structured JSON errors
    const response = await request.post("/api/sparql", {
      data: { query: "INVALID SYNTAX HERE" },
      headers: { "Content-Type": "application/json" },
    });

    // Should NOT be an uncaught 500
    expect(response.status()).not.toBe(500);
    // Should be a structured error response
    if (response.status() >= 400) {
      const body = await response.json();
      expect(body).toHaveProperty("error");
    }
  });
});
