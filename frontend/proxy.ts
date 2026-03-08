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

export function proxy(req: NextRequest) {
  // Check for the cookie we set in the /api/auth-exchange route
  const sessionCookie = req.cookies.get("iqoqo_session");
  const isLoggedIn = !!sessionCookie?.value;
  const isAuthPage = req.nextUrl.pathname.startsWith('/login');

  // If they are on the login page but already logged in, send them to Discover
  if (isAuthPage) {
    if (isLoggedIn) {
      return NextResponse.redirect(new URL('/discover', req.nextUrl));
    }
    return NextResponse.next();
  }

  // If they are NOT logged in, redirect them to the login page
  if (!isLoggedIn) {
    // Optional: save the page they tried to visit so you can redirect them back after login
    const loginUrl = new URL('/login', req.nextUrl);
    // loginUrl.searchParams.set('callbackUrl', req.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// The matcher defines which routes this middleware runs on.
// This runs on everything EXCEPT /api, static files, and images.
export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
