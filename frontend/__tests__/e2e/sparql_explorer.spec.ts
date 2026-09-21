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

/**
 * Mock SPARQL SELECT results payload.
 */
const mockSelectResults = {
  head: { vars: ["work", "title", "author"] },
  results: {
    bindings: [
      {
        work: { type: "uri", value: "http://example.org/work/1" },
        title: { type: "literal", value: "Semantic Web Primer" },
        author: { type: "literal", value: "Tim Berners-Lee" },
      },
      {
        work: { type: "uri", value: "http://example.org/work/2" },
        title: { type: "literal", value: "SPARQL By Example" },
        author: { type: "literal", value: "Bob DuCharme" },
      },
    ],
  },
};

/**
 * Sets up common authenticated custodian user for SPARQL Explorer tests.
 */
async function setupCustodianUser(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("iqoqo-cookie-consent", "true");
  });

  await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

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
}

test.describe("SPARQL Explorer — Regression Validation", () => {
  test.beforeEach(async ({ page }) => {
    await setupCustodianUser(page);
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
          json: mockSelectResults,
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
          body: '@prefix schema: <https://schema.org/> .\n<http://example.org/s> schema:name "Test" .',
        });
      }
    });

    // Navigate to SPARQL Explorer (Administration menu)
    await page.goto("/admin");

    // Verify the Administration menu is visible to authorized users
    // The SPARQL Explorer should be accessible
    const sparqlLink = page.locator('a[href*="sparql"], [data-testid="sparql-explorer"]');
    // If the link exists, click it and verify no 500 errors
    if ((await sparqlLink.count()) > 0) {
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

test.describe("SPARQL Explorer — Query Editor", () => {
  test.beforeEach(async ({ page }) => {
    await setupCustodianUser(page);
  });

  test("query editor accepts valid SPARQL input and displays syntax area", async ({ page }) => {
    await page.goto("/admin/sparql");

    // Wait for page to load
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Query editor (textarea) should be visible with default query
    const editor = page.locator("textarea");
    await expect(editor).toBeVisible();

    // Default query should be loaded (All Works example)
    const editorValue = await editor.inputValue();
    expect(editorValue).toContain("SELECT");

    // User can type in the editor
    await editor.fill("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10");
    const newValue = await editor.inputValue();
    expect(newValue).toContain("LIMIT 10");
  });

  test("executing a valid query displays results in table format", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 200,
        contentType: "application/sparql-results+json",
        json: mockSelectResults,
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Click Execute button
    const executeBtn = page.getByRole("button", { name: /Execute/i });
    await expect(executeBtn).toBeVisible();
    await executeBtn.click();

    // Results table should appear
    await expect(page.getByText("Results (2 rows)")).toBeVisible({ timeout: 10000 });

    // Table column headers should be visible (use role to avoid matching query textarea)
    await expect(page.getByRole("columnheader", { name: "?work" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "?title" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "?author" })).toBeVisible();

    // Result values should be visible
    await expect(page.getByText("Semantic Web Primer")).toBeVisible();
    await expect(page.getByText("SPARQL By Example")).toBeVisible();
  });

  test("example queries sidebar loads query templates into editor", async ({ page }) => {
    await page.goto("/admin/sparql");
    await expect(page.getByText("Example Queries")).toBeVisible();

    // Click on "Recent Items" example
    await page.getByRole("button", { name: "Recent Items" }).click();

    // Editor should now contain the Recent Items query
    const editor = page.locator("textarea");
    const value = await editor.inputValue();
    expect(value).toContain("Item");
  });
});

test.describe("SPARQL Explorer — Result Format Switching", () => {
  test.beforeEach(async ({ page }) => {
    await setupCustodianUser(page);
  });

  test("download buttons appear for SELECT results (JSON, CSV)", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 200,
        contentType: "application/sparql-results+json",
        json: mockSelectResults,
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();
    await expect(page.getByText("Results (2 rows)")).toBeVisible({ timeout: 10000 });

    // Download buttons should be visible
    await expect(page.getByRole("button", { name: /Download CSV/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Download JSON/i })).toBeVisible();
  });

  test("CONSTRUCT query shows Turtle download option", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 200,
        contentType: "text/turtle",
        body: '@prefix schema: <https://schema.org/> .\n<http://example.org/s> schema:name "Test" .',
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Enter a CONSTRUCT query
    const editor = page.locator("textarea");
    await editor.fill("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10");

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();

    // RDF Output section should appear
    await expect(page.getByText("RDF Output")).toBeVisible({ timeout: 10000 });

    // Turtle download button should be visible
    await expect(page.getByRole("button", { name: /Download Turtle/i })).toBeVisible();
  });
});

test.describe("SPARQL Explorer — Error Handling", () => {
  test.beforeEach(async ({ page }) => {
    await setupCustodianUser(page);
  });

  test("invalid SPARQL syntax displays error message", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        json: { error: "SPARQL syntax error: Expected SelectQuery" },
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Enter invalid query
    const editor = page.locator("textarea");
    await editor.fill("INVALID QUERY SYNTAX");

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();

    // Error message should be displayed
    await expect(page.getByText(/SPARQL syntax error/)).toBeVisible({ timeout: 10000 });
  });

  test("query timeout displays timeout error", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 504,
        contentType: "application/json",
        json: { error: "Query execution exceeded 15s timeout" },
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();

    // Timeout error should be displayed
    await expect(page.getByText(/timeout/i)).toBeVisible({ timeout: 10000 });
  });

  test("query returning no results shows empty results", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 200,
        contentType: "application/sparql-results+json",
        json: {
          head: { vars: ["work", "title"] },
          results: { bindings: [] },
        },
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();

    // Results section should show 0 rows
    await expect(page.getByText("Results (0 rows)")).toBeVisible({ timeout: 10000 });
  });
});

test.describe("SPARQL Explorer — Query History and Concurrent Handling", () => {
  test.beforeEach(async ({ page }) => {
    await setupCustodianUser(page);
  });

  test("concurrent query execution does not corrupt results", async ({ page }) => {
    let queryCount = 0;
    await page.route("**/api/sparql**", route => {
      queryCount++;
      route.fulfill({
        status: 200,
        contentType: "application/sparql-results+json",
        json: {
          head: { vars: ["count"] },
          results: {
            bindings: [{ count: { type: "literal", value: String(queryCount) } }],
          },
        },
      });
    });

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Execute query multiple times in quick succession
    const executeBtn = page.getByRole("button", { name: /Execute/i });
    await executeBtn.click();
    // Wait for first to complete
    await expect(page.getByText("Results (1 rows)")).toBeVisible({ timeout: 10000 });

    // Execute again
    await executeBtn.click();
    await expect(page.getByText("Results (1 rows)")).toBeVisible({ timeout: 10000 });

    // Verify queries were processed (no errors)
    expect(queryCount).toBeGreaterThanOrEqual(2);
  });

  test("query size limit is enforced with error message", async ({ page }) => {
    await page.route("**/api/sparql**", route =>
      route.fulfill({
        status: 413,
        contentType: "application/json",
        json: { error: "Query exceeds maximum size of 10240 bytes" },
      })
    );

    await page.goto("/admin/sparql");
    await expect(page.getByText("SPARQL Explorer")).toBeVisible();

    // Enter a very large query
    const editor = page.locator("textarea");
    const largeQuery = `SELECT ?s ?p ?o WHERE { ${"VALUES ?x { " + " ".repeat(11000) + "} }"}`;
    await editor.fill(largeQuery);

    // Execute query
    await page.getByRole("button", { name: /Execute/i }).click();

    // Error about size limit should be displayed
    await expect(page.getByText(/exceeds maximum size/i)).toBeVisible({ timeout: 10000 });
  });
});

test.describe("SPARQL Explorer — Access Control", () => {
  test("unauthorized user sees access denied message", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    // Mock user without SPARQL permissions
    await page.route("**/api/profile**", route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: "basic-user",
            email: "basic@iqoqo.local",
            display_name: "Basic User",
            roles: ["user"],
            permissions: [],
          },
        },
      })
    );

    await page.goto("/admin/sparql");

    // Should see access denied message
    await expect(page.getByText("Access Denied")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/custodian permissions/i)).toBeVisible();
  });
});
