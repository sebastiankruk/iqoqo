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

/**
 * Middleware function for routing and auth checks.
 *
 * @param req - The Next.js request
 * @returns {NextResponse} The Next.js response
 */
export function proxy(req: NextRequest) {
  // Check for the cookie we set in the /api/auth-exchange route
  const sessionCookie = req.cookies.get("iqoqo_session");
  const isLoggedIn = !!sessionCookie?.value;
  const pathname = req.nextUrl.pathname;

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
