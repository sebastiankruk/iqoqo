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
import { POST as apiPost } from "@/app/api/auth-exchange/route";

const mockCookieSet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: async () => ({
    set: mockCookieSet,
  }),
}));

afterEach(() => {
  mockCookieSet.mockReset();
  vi.unstubAllGlobals();
});

describe("Auth Exchange POST Handler", () => {
  it("exchanges token via POST JSON body and sets session cookie", async () => {
    mockCookieSet.mockClear();
    const req = new Request("http://localhost:3000/api/auth-exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: "jwt-sample-token-12345", callbackUrl: "/dashboard" }),
    });

    const res = await apiPost(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.redirectUrl).toBe("http://localhost:3000/dashboard");

    expect(mockCookieSet).toHaveBeenCalledWith(
      "iqoqo_session",
      "jwt-sample-token-12345",
      expect.objectContaining({
        httpOnly: true,
        path: "/",
      })
    );
  });

  it("exchanges code via POST JSON body", async () => {
    mockCookieSet.mockClear();
    const backendFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ token: "exchanged-session-jwt", callbackUrl: "/" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", backendFetch);
    const req = new Request("http://localhost:3000/api/auth-exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: "oauth-code-xyz" }),
    });

    const res = await apiPost(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.redirectUrl).toBe("http://localhost:3000/");
    expect(backendFetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/auth\/exchange$/),
      expect.objectContaining({ method: "POST", body: JSON.stringify({ code: "oauth-code-xyz" }) })
    );

    expect(mockCookieSet).toHaveBeenCalledWith(
      "iqoqo_session",
      "exchanged-session-jwt",
      expect.objectContaining({
        httpOnly: true,
        path: "/",
      })
    );
  });

  it("returns 400 if token/code is missing in POST body", async () => {
    mockCookieSet.mockClear();
    const req = new Request("http://localhost:3000/api/auth-exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    const res = await apiPost(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.success).toBe(false);
    expect(data.error).toBe("Missing token or code");
  });
});
