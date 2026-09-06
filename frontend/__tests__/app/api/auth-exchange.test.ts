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
import { describe, it, expect, vi } from "vitest";
import { GET } from "@/app/api/auth-exchange/route";

vi.mock("next/headers", () => ({
  cookies: async () => ({
    set: vi.fn(),
  }),
}));

describe("auth-exchange route handler", () => {
  it("redirects to login error if token is missing", async () => {
    const req = new Request("http://localhost:3000/api/auth-exchange");
    const res = await GET(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login?error=MissingToken");
  });

  it("redirects to callbackUrl after successful token exchange if provided", async () => {
    const req = new Request(
      "http://localhost:3000/api/auth-exchange?token=abc123&callbackUrl=%2Fcollection%3Fstatuses%3Dwishlist"
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/collection?statuses=wishlist");
  });

  it("redirects to / after successful token exchange if callbackUrl is missing", async () => {
    const req = new Request("http://localhost:3000/api/auth-exchange?token=abc123");
    const res = await GET(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("respects x-forwarded-host and x-forwarded-proto headers", async () => {
    const req = new Request("http://internal-node:3000/api/auth-exchange?token=abc123", {
      headers: {
        "x-forwarded-host": "pre.iqoqo.cc:8000",
        "x-forwarded-proto": "http",
      },
    });
    const res = await GET(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://pre.iqoqo.cc:8000/");
  });

  it("rejects poisoned x-forwarded-host header from unauthorized domains and falls back to request url host", async () => {
    const req = new Request("http://localhost:3000/api/auth-exchange?token=abc123", {
      headers: {
        "x-forwarded-host": "evil.com",
        "x-forwarded-proto": "https",
      },
    });
    const res = await GET(req);
    expect(res.status).toBe(307);
    // Should NOT redirect to evil.com
    expect(res.headers.get("location")).not.toContain("evil.com");
    expect(res.headers.get("location")).toBe("https://localhost:3000/");
  });

  it("prioritizes NEXT_PUBLIC_FRONTEND_URL environment variable over request host", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_FRONTEND_URL;
    process.env.NEXT_PUBLIC_FRONTEND_URL = "https://custom.iqoqo.local:9000";
    try {
      const req = new Request("http://localhost:3000/api/auth-exchange?token=abc123");
      const res = await GET(req);
      expect(res.status).toBe(307);
      expect(res.headers.get("location")).toBe("https://custom.iqoqo.local:9000/");
    } finally {
      process.env.NEXT_PUBLIC_FRONTEND_URL = originalEnv;
    }
  });

  it("rejects poisoned host header and falls back securely to localhost:3000", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_FRONTEND_URL;
    delete process.env.NEXT_PUBLIC_FRONTEND_URL;
    try {
      const req = new Request("http://evil.com/api/auth-exchange?token=abc123", {
        headers: {
          host: "evil.com",
        },
      });
      const res = await GET(req);
      expect(res.status).toBe(307);
      expect(res.headers.get("location")).not.toContain("evil.com");
      expect(res.headers.get("location")).toBe("http://localhost:3000/");
    } finally {
      process.env.NEXT_PUBLIC_FRONTEND_URL = originalEnv;
    }
  });
});
