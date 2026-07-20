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
import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "@/proxy";

describe("proxy middleware redirect rules", () => {
  it("redirects unauthenticated access to /profile to /login with callbackUrl", () => {
    const req = new NextRequest("http://localhost:3000/profile");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?callbackUrl=%2Fprofile");
  });

  it("redirects unauthenticated access to /collection?statuses=wishlist preserving query parameters", () => {
    const req = new NextRequest("http://localhost:3000/collection?statuses=wishlist");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost:3000/login?callbackUrl=%2Fcollection%3Fstatuses%3Dwishlist"
    );
  });

  it("redirects unauthenticated access to /scan to /login with callbackUrl", () => {
    const req = new NextRequest("http://localhost:3000/scan");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?callbackUrl=%2Fscan");
  });

  it("redirects unauthenticated access to /admin to /login with callbackUrl", () => {
    const req = new NextRequest("http://localhost:3000/admin/settings");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?callbackUrl=%2Fadmin%2Fsettings");
  });

  it("allows authenticated access to protected routes", () => {
    const req = new NextRequest("http://localhost:3000/collection");
    req.cookies.set("iqoqo_session", "valid_token");
    const res = proxy(req);
    expect(res.headers.get("location")).toBeNull();
  });

  it("redirects logged-in user on /login to callbackUrl if provided", () => {
    const req = new NextRequest("http://localhost:3000/login?callbackUrl=%2Fcollection%3Fstatuses%3Dwishlist");
    req.cookies.set("iqoqo_session", "valid_token");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/collection?statuses=wishlist");
  });

  it("redirects logged-in user on /login to /profile if callbackUrl not provided", () => {
    const req = new NextRequest("http://localhost:3000/login");
    req.cookies.set("iqoqo_session", "valid_token");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/profile");
  });
});
