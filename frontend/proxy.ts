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
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import * as jose from 'jose';

const SECRET_KEY = new TextEncoder().encode(process.env.JWT_SECRET_KEY || "you-will-never-guess");
const PROTECTED_ROUTES = ['/collection', '/item', '/settings', '/profile', '/scan'];
const ADMIN_ROUTES = ['/admin'];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_ROUTES.some(route => pathname.startsWith(route));
  const isAdminRoute = ADMIN_ROUTES.some(route => pathname.startsWith(route));

  if (!isProtected && !isAdminRoute) return NextResponse.next();

  const token = request.cookies.get('iqoqo_session')?.value;
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  try {
    const { payload } = await jose.jwtVerify(token, SECRET_KEY);

    if (isAdminRoute) {
      const roles = payload.roles as string[];
      if (!roles || !roles.includes('admin')) {
        return NextResponse.rewrite(new URL('/unauthorized', request.url));
      }
    }

    const requestHeaders = new Headers(request.headers);
    requestHeaders.set('x-user-id', payload.sub as string);
    return NextResponse.next({ request: { headers: requestHeaders } });

  } catch (error) {
    console.error("Proxy auth error:", error);
    const response = NextResponse.redirect(new URL('/login?error=SessionExpired', request.url));
    response.cookies.delete('iqoqo_session');
    return response;
  }
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
