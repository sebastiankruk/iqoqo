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

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "@/proxy";

describe("proxy runtime share feed rewrites and content negotiation", () => {
  const originalFlaskUrl = process.env.FLASK_API_URL;
  const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    delete process.env.FLASK_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterEach(() => {
    if (originalFlaskUrl === undefined) delete process.env.FLASK_API_URL;
    else process.env.FLASK_API_URL = originalFlaskUrl;

    if (originalPublicApiUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = originalPublicApiUrl;
  });

  it("rewrites /share/:token/catalog.jsonld using runtime FLASK_API_URL", () => {
    process.env.FLASK_API_URL = "http://web:5000/api";
    const req = new NextRequest("https://preview.iqoqo.cc/share/tok-123/catalog.jsonld?limit=2000");
    const res = proxy(req);

    expect(res.headers.get("x-middleware-rewrite")).toBe(
      "http://web:5000/api/public/share/tok-123?limit=2000&format=jsonld"
    );
  });

  it("rewrites /share/:token/feed.xml using runtime FLASK_API_URL", () => {
    process.env.FLASK_API_URL = "http://web:5000/api";
    const req = new NextRequest("https://preview.iqoqo.cc/share/tok-123/feed.xml");
    const res = proxy(req);

    expect(res.headers.get("x-middleware-rewrite")).toBe("http://web:5000/api/public/share/tok-123/feed.xml");
  });

  it("negotiates Accept: application/ld+json and application/json+ld on canonical /share/:token", () => {
    process.env.FLASK_API_URL = "http://web:5000/api";

    for (const accept of ["application/ld+json", "application/json+ld", "text/turtle"]) {
      const req = new NextRequest("https://preview.iqoqo.cc/share/tok-123?page=2", {
        headers: { accept },
      });
      const res = proxy(req);
      expect(res.headers.get("x-middleware-rewrite")).toBe("http://web:5000/api/public/share/tok-123?page=2");
    }
  });

  it("does not rewrite canonical /share/:token for text/html browsers", () => {
    process.env.FLASK_API_URL = "http://web:5000/api";
    const req = new NextRequest("https://preview.iqoqo.cc/share/tok-123?page=2", {
      headers: { accept: "text/html,application/xhtml+xml" },
    });
    const res = proxy(req);

    expect(res.headers.get("x-middleware-rewrite")).toBeNull();
  });

  it("ignores relative NEXT_PUBLIC_API_URL and falls back to 127.0.0.1:5000", () => {
    process.env.NEXT_PUBLIC_API_URL = "/api";
    const req = new NextRequest("http://localhost:3000/share/tok-123/catalog.jsonld");
    const res = proxy(req);

    expect(res.headers.get("x-middleware-rewrite")).toBe(
      "http://127.0.0.1:5000/api/public/share/tok-123?format=jsonld"
    );
  });

  it("still redirects unauthenticated protected routes to /login", () => {
    const req = new NextRequest("https://preview.iqoqo.cc/collection");
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login?callbackUrl=%2Fcollection");
  });
});
