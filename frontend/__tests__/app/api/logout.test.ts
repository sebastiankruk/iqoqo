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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieDelete = vi.fn();
let mockToken: string | undefined;

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: (name: string) => (name === "iqoqo_session" ? { value: mockToken } : undefined) }),
}));

vi.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown) => ({ body, cookies: { delete: mockCookieDelete } }),
  },
}));

import { POST } from "@/app/api/auth/logout/route";

/**
 * Assert that Flask's revocation endpoint was reached with the session token.
 *
 * The route under test is a Next handler at the same path as the Flask logout
 * endpoint, and Next handlers shadow the `/api/:path*` rewrite. So whether the
 * token is ever revoked depends entirely on this handler calling through --
 * nothing else in the stack will.
 *
 * @returns Nothing; a missing or unauthenticated call fails the test.
 */
function expectRevocation(): void {
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = vi.mocked(fetch).mock.calls[0];
  expect(String(url)).toMatch(/\/auth\/logout$/);
  expect(init?.method).toBe("POST");
  expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer session-token-value");
}

describe("POST /api/auth/logout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockToken = "session-token-value";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200 }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("revokes the token with the backend before clearing the cookie", async () => {
    // The regression this pins: the handler used to delete the cookie and
    // nothing else. The JWT in it stays valid until it expires, so logout was
    // cosmetic -- any copy of the token kept working after signing out.
    const response = await POST();

    expectRevocation();
    expect(mockCookieDelete).toHaveBeenCalledWith("iqoqo_session");
    expect(response.body).toEqual({ success: true, message: "Logged out successfully" });
  });

  it("sends the revocation as a Bearer header rather than relying on cookie forwarding", async () => {
    // Flask's endpoint accepts either an Authorization header or the
    // iqoqo_session cookie. Forwarding it explicitly keeps the call independent
    // of cookie-forwarding semantics on the server-to-server request.
    await POST();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(Object.keys(init?.headers as object)).toEqual(["Authorization"]);
  });

  it("still clears the cookie when the backend cannot be reached", async () => {
    // Logout must never be blocked by a backend hiccup. Leaving the cookie in
    // place would leave the user signed in against their explicit request,
    // which is worse than a token the backend failed to revoke.
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED")));

    const response = await POST();

    expect(mockCookieDelete).toHaveBeenCalledWith("iqoqo_session");
    expect(response.body).toMatchObject({ success: true });
  });

  it("still clears the cookie when the backend rejects the revocation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await POST();

    expect(mockCookieDelete).toHaveBeenCalledWith("iqoqo_session");
  });

  it("skips the backend call when there is no session cookie", async () => {
    // No cookie means no token to revoke. Calling anyway would send
    // `Bearer undefined`.
    mockToken = undefined;

    await POST();

    expect(fetch).not.toHaveBeenCalled();
    expect(mockCookieDelete).toHaveBeenCalledWith("iqoqo_session");
  });

  it("marks the revocation uncacheable", async () => {
    // A cached POST response would leave a stale revocation unreplayed for a
    // later request.
    await POST();

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.cache).toBe("no-store");
  });
});
