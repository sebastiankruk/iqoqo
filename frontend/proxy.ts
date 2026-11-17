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
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const RDF_ACCEPT_MIME_TYPES = [
  "application/ld+json",
  "application/json+ld",
  "text/turtle",
  "application/x-turtle",
  "application/n-triples",
  "application/rdf+xml",
];

/**
 * Resolves the internal Flask backend base URL at request time (never baked at build time).
 */
function resolveRuntimeBackendBase(): string {
  const candidates = [process.env.FLASK_API_URL, process.env.NEXT_PUBLIC_API_URL];
  for (const raw of candidates) {
    if (!raw) continue;
    const stripped = raw.replace(/\/api\/?$/, "");
    if (stripped.startsWith("http://") || stripped.startsWith("https://")) {
      return stripped;
    }
  }
  return "http://127.0.0.1:5000";
}

/**
 * Middleware function for routing and auth checks.
 *
 * @param req - The Next.js request
 * @returns {NextResponse} The Next.js response
 */
export function proxy(req: NextRequest) {
  const pathname = req.nextUrl.pathname;

  // Runtime rewrite for non-/api/ shared collection semantic feeds so prebuilt
  // standalone Docker images respect runtime FLASK_API_URL (e.g. http://web:5000/api).
  const shareFeedMatch = pathname.match(/^\/share\/([^/]+)\/(catalog\.jsonld|feed\.xml)$/);
  if (shareFeedMatch) {
    const [, token, feedFile] = shareFeedMatch;
    const backendBase = resolveRuntimeBackendBase();
    const target =
      feedFile === "catalog.jsonld"
        ? new URL(`${backendBase}/api/public/share/${encodeURIComponent(token)}`)
        : new URL(`${backendBase}/api/public/share/${encodeURIComponent(token)}/feed.xml`);
    req.nextUrl.searchParams.forEach((value, key) => {
      target.searchParams.set(key, value);
    });
    if (feedFile === "catalog.jsonld" && !target.searchParams.has("format")) {
      target.searchParams.set("format", "jsonld");
    }
    return NextResponse.rewrite(target);
  }

  // HTTP Content Negotiation on canonical /share/<token> (and ?page=N):
  // clients requesting application/ld+json, application/json+ld, or RDF formats
  // are routed directly to Flask's RDF/JSON-LD serializer.
  const canonicalShareMatch = pathname.match(/^\/share\/([^/]+)\/?$/);
  if (canonicalShareMatch) {
    const acceptHeader = (req.headers.get("accept") || "").toLowerCase();
    if (RDF_ACCEPT_MIME_TYPES.some(mime => acceptHeader.includes(mime))) {
      const [, token] = canonicalShareMatch;
      const target = new URL(`${resolveRuntimeBackendBase()}/api/public/share/${encodeURIComponent(token)}`);
      req.nextUrl.searchParams.forEach((value, key) => {
        target.searchParams.set(key, value);
      });
      return NextResponse.rewrite(target);
    }
  }

  // Check for the cookie we set in the /api/auth-exchange route
  const sessionCookie = req.cookies.get("iqoqo_session");
  const isLoggedIn = !!sessionCookie?.value;

  // Protected routes – require authentication
  const protectedRoutes = ["/profile", "/collection", "/scan", "/admin"];
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

  // If they are on the login page but already logged in, redirect to callbackUrl or /profile
  if (pathname.startsWith("/login")) {
    if (isLoggedIn) {
      const callbackUrl = req.nextUrl.searchParams.get("callbackUrl") || req.nextUrl.searchParams.get("redirect");
      const target =
        callbackUrl && callbackUrl.startsWith("/") && !callbackUrl.startsWith("//") ? callbackUrl : "/profile";
      return NextResponse.redirect(new URL(target, req.nextUrl));
    }
    return NextResponse.next();
  }

  // If they are NOT logged in AND trying to access a protected route, redirect to login
  if (!isLoggedIn && isProtectedRoute) {
    const loginUrl = new URL("/login", req.nextUrl);
    const fullTarget = pathname + req.nextUrl.search;
    loginUrl.searchParams.set("callbackUrl", fullTarget);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// The matcher defines which routes this middleware runs on.
// This runs on everything EXCEPT /api, static files, and images.
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
