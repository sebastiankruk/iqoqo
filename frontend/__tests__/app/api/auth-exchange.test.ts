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
import { afterEach, describe, it, expect, vi } from "vitest";
import { GET, POST } from "@/app/api/auth-exchange/route";

const { mockCookieSet } = vi.hoisted(() => ({ mockCookieSet: vi.fn() }));
const originalFlaskApiUrl = process.env.FLASK_API_URL;
const originalFrontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL;

vi.mock("next/headers", () => ({
  cookies: async () => ({ set: mockCookieSet }),
}));

function installExchangeResponse(payload: object, status = 200) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } })
    );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  mockCookieSet.mockReset();
  vi.unstubAllGlobals();
  if (originalFlaskApiUrl === undefined) delete process.env.FLASK_API_URL;
  else process.env.FLASK_API_URL = originalFlaskApiUrl;
  if (originalFrontendUrl === undefined) delete process.env.NEXT_PUBLIC_FRONTEND_URL;
  else process.env.NEXT_PUBLIC_FRONTEND_URL = originalFrontendUrl;
});

describe("auth-exchange route handler", () => {
  it("rejects requests without a one-time code", async () => {
    const fetchMock = installExchangeResponse({ token: "must-not-be-used" });
    const response = await GET(new Request("http://localhost:3000/api/auth-exchange"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login?error=oauth_exchange_failed");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(mockCookieSet).not.toHaveBeenCalled();
  });

  it("never accepts a persistent JWT from a query parameter", async () => {
    const fetchMock = installExchangeResponse({ token: "must-not-be-used" });
    const response = await GET(new Request("http://localhost:3000/api/auth-exchange?token=legacy-jwt"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login?error=oauth_exchange_failed");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(mockCookieSet).not.toHaveBeenCalled();
  });

  it("exchanges the one-time code with Flask via POST and redirects to a clean URL", async () => {
    process.env.FLASK_API_URL = "http://flask.internal:5000/api/";
    const fetchMock = installExchangeResponse({
      token: "internal-session-jwt",
      callbackUrl: "/collection?view=roadmap",
    });
    const response = await GET(new Request("https://localhost:3000/api/auth-exchange?code=ephemeral-code"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://flask.internal:5000/api/auth/exchange",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
        redirect: "error",
        body: JSON.stringify({ code: "ephemeral-code" }),
      })
    );
    expect(mockCookieSet).toHaveBeenCalledWith(
      "iqoqo_session",
      "internal-session-jwt",
      expect.objectContaining({ httpOnly: true, secure: true, sameSite: "lax", path: "/" })
    );
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://localhost:3000/collection?view=roadmap");
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("referrer-policy")).toBe("no-referrer");
    expect(response.headers.get("location")).not.toContain("ephemeral-code");
  });

  it("does not set a cookie when Flask rejects or cannot exchange the code", async () => {
    installExchangeResponse({ error: "Invalid code" }, 400);
    const response = await GET(new Request("http://localhost:3000/api/auth-exchange?code=expired-code"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login?error=oauth_exchange_failed");
    expect(mockCookieSet).not.toHaveBeenCalled();
  });

  it("preserves local-login JWT exchange in a POST body", async () => {
    const response = await POST(
      new Request("http://localhost:3000/api/auth-exchange?token=ignored", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: "local-login-jwt", callbackUrl: "/collection" }),
      })
    );

    expect(response.status).toBe(200);
    expect(mockCookieSet).toHaveBeenCalledWith(
      "iqoqo_session",
      "local-login-jwt",
      expect.objectContaining({ httpOnly: true, path: "/" })
    );
    expect((await response.json()).redirectUrl).toBe("http://localhost:3000/collection");
  });

  it("exchanges an authorization code submitted in a POST body", async () => {
    process.env.FLASK_API_URL = "http://flask.internal:5000/api";
    const fetchMock = installExchangeResponse({ token: "exchanged-jwt", callbackUrl: "/" });
    const response = await POST(
      new Request("http://localhost:3000/api/auth-exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "ephemeral-code" }),
      })
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mockCookieSet).toHaveBeenCalledWith("iqoqo_session", "exchanged-jwt", expect.any(Object));
  });

  it("rejects poisoned forwarded hosts and keeps redirects on an allowed host", async () => {
    installExchangeResponse({ token: "internal-session-jwt", callbackUrl: "/" });
    const response = await GET(
      new Request("http://localhost:3000/api/auth-exchange?code=ephemeral-code", {
        headers: { "x-forwarded-host": "evil.example", "x-forwarded-proto": "https" },
      })
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://localhost:3000/");
    expect(response.headers.get("location")).not.toContain("evil.example");
  });
});
