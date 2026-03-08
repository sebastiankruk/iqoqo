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
