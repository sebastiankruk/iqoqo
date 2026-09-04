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
});
