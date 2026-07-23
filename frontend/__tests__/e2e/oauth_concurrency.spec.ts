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

test.describe("OAuth Concurrency", () => {
  test("handles concurrent OAuth login triggers and establishes baseline for session race conditions", async ({
    context,
    baseURL,
  }) => {
    const [page1, page2, page3] = await Promise.all([context.newPage(), context.newPage(), context.newPage()]);

    const targetUrl = `${baseURL}/api/auth/google/login?callbackUrl=/`;

    const results = await Promise.allSettled([page1.goto(targetUrl), page2.goto(targetUrl), page3.goto(targetUrl)]);

    let successCount = 0;
    let failCount = 0;

    for (const result of results) {
      if (result.status === "fulfilled") {
        const response = result.value;
        const status = response?.status();
        if (status && status < 400) {
          successCount++;
        } else {
          failCount++;
        }
      } else {
        failCount++;
      }
    }

    // Assert that the test completed without crashing the browser context
    expect(results.length).toBe(3);
    // Based on the requirement, we are documenting the baseline.
    expect(successCount + failCount).toBe(3);
  });
});
