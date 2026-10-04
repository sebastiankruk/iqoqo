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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * The CSRF-header behaviour of `frontend/lib/api/account.ts`.
 *
 * Kept in its own file, and with `@/lib/api/account` *not* mocked. A hoisted
 * `vi.mock` of the module under test replaces it in dynamic imports too, so
 * testing it from the component file meant asserting against the mock rather
 * than the code.
 */
describe("account API client CSRF handling", () => {
  const originalCookie = Object.getOwnPropertyDescriptor(document, "cookie");

  beforeEach(() => {
    // `resetModules` re-imports the modules under test but does NOT re-run
    // `vitest.setup.ts`, so the axios instance created there is a process-wide
    // singleton whose call log leaks between tests. Clearing explicitly is what
    // makes each assertion about its own two calls rather than every call so far.
    vi.resetModules();
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Restore the real accessor, so a stubbed cookie in one test cannot silently
    // disable CSRF coverage in the next.
    if (originalCookie) Object.defineProperty(document, "cookie", originalCookie);
    vi.restoreAllMocks();
  });

  /**
   * Stub `document.cookie` so it reports a fixed CSRF value.
   *
   * @param value - The token to report, or an empty string for no cookie
   */
  function stubCsrfCookie(value: string): void {
    Object.defineProperty(document, "cookie", {
      configurable: true,
      get: () => (value ? `iqoqo_csrf=${value}; other=1` : "other=1"),
    });
  }

  it("attaches the CSRF header when the cookie is present", async () => {
    stubCsrfCookie("signed-token-value");
    const { apiClient } = await import("@/lib/api/client");
    const { requestAccountDeletion } = await import("@/lib/api/account");
    vi.mocked(apiClient.request).mockResolvedValue({ data: {} } as never);

    await requestAccountDeletion();

    expect(apiClient.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "POST",
        url: "/account/deletion/request",
        headers: { "X-CSRF-Token": "signed-token-value" },
      })
    );
  });

  it("omits the header when no CSRF cookie exists", async () => {
    // A bearer-token client has nothing to prove, and the backend does not
    // require proof for it. Sending an empty header would produce a 403 in a
    // context where none was asked for.
    stubCsrfCookie("");
    const { apiClient } = await import("@/lib/api/client");
    const { requestAccountDeletion } = await import("@/lib/api/account");
    vi.mocked(apiClient.request).mockResolvedValue({ data: {} } as never);

    await requestAccountDeletion();

    const config = vi.mocked(apiClient.request).mock.calls[0][0] as { headers?: Record<string, string> };
    expect(config.headers).toBeUndefined();
  });

  it("reads the cookie value and not a stale copy from module state", async () => {
    // The value is read per request, so a rotated cookie is honoured rather than
    // a captured one going stale and causing unexplained 403s.
    stubCsrfCookie("first-value");
    const { apiClient } = await import("@/lib/api/client");
    const { requestAccountDeletion } = await import("@/lib/api/account");
    vi.mocked(apiClient.request).mockResolvedValue({ data: {} } as never);

    await requestAccountDeletion();

    Object.defineProperty(document, "cookie", {
      configurable: true,
      get: () => "iqoqo_csrf=second-value",
    });

    await requestAccountDeletion();

    const calls = vi
      .mocked(apiClient.request)
      .mock.calls.map(c => (c[0] as { headers?: Record<string, string> }).headers);
    expect(calls).toEqual([{ "X-CSRF-Token": "first-value" }, { "X-CSRF-Token": "second-value" }]);
  });

  it("sends the new address as a JSON body on change", async () => {
    stubCsrfCookie("tok");
    const { apiClient } = await import("@/lib/api/client");
    const { changeAccountEmail } = await import("@/lib/api/account");
    vi.mocked(apiClient.request).mockResolvedValue({
      data: { success: true, data: { email: "new@iqoqo.local", email_verified: false, verification_email_sent: true } },
    } as never);

    const result = await changeAccountEmail("new@iqoqo.local");

    expect(apiClient.request).toHaveBeenCalledWith(
      expect.objectContaining({ method: "PUT", url: "/account/email", data: { email: "new@iqoqo.local" } })
    );
    expect(result.verification_email_sent).toBe(true);
  });

  it("surfaces a rejected address change rather than swallowing it", async () => {
    stubCsrfCookie("tok");
    const { apiClient } = await import("@/lib/api/client");
    const { changeAccountEmail } = await import("@/lib/api/account");
    vi.mocked(apiClient.request).mockRejectedValue(new Error("That email address is already registered"));

    await expect(changeAccountEmail("taken@iqoqo.local")).rejects.toThrow(/already registered/);
  });
});
