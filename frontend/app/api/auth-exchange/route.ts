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
// frontend/app/api/auth-exchange/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

/**
 * Validates whether a hostname belongs to an allowed deployment domain.
 *
 * @param hostWithPort - The hostname, optionally including a port
 * @returns {boolean} True if the host is allowed, false otherwise
 */
function isAllowedHost(hostWithPort: string): boolean {
  const host = hostWithPort.split(":")[0].toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "iqoqo.cc" || host.endsWith(".iqoqo.cc");
}

/**
 * Handle GET requests to exchange a short-lived token for a session cookie.
 *
 * @param request - The incoming Next.js request
 * @returns {Promise<NextResponse>} The Next.js response redirecting to the dashboard
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const { searchParams } = url;
  const token = searchParams.get("token");

  const rawForwardedHost = request.headers.get("x-forwarded-host");
  const rawHostHeader = request.headers.get("host") || "";

  // Fail-closed fallback: never trust raw request host if validation fails
  const fallbackHost = process.env.NEXT_PUBLIC_FRONTEND_URL
    ? new URL(process.env.NEXT_PUBLIC_FRONTEND_URL).host
    : "localhost:3000";

  // Enforce host validation to prevent arbitrary open redirects via poisoned headers
  const effectiveHost =
    rawForwardedHost && isAllowedHost(rawForwardedHost)
      ? rawForwardedHost
      : rawHostHeader && isAllowedHost(rawHostHeader)
        ? rawHostHeader
        : fallbackHost;

  const forwardedProto = request.headers.get("x-forwarded-proto");
  const effectiveProto =
    forwardedProto === "https" || forwardedProto === "http"
      ? forwardedProto
      : url.protocol.startsWith("https")
        ? "https"
        : "http";

  const isHttps = effectiveProto === "https";
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || `${effectiveProto}://${effectiveHost}`;

  if (!token) {
    return NextResponse.redirect(new URL("/login?error=MissingToken", baseUrl));
  }

  // Set the HttpOnly cookie (secure only when served over HTTPS)
  const cookieStore = await cookies();
  cookieStore.set("iqoqo_session", token, {
    httpOnly: true,
    secure: isHttps,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // 7 days
  });

  // Redirect to specified callbackUrl or default target explicitly using the correct domain
  const callbackUrl = searchParams.get("callbackUrl") || searchParams.get("redirect");
  const target = callbackUrl && callbackUrl.startsWith("/") && !callbackUrl.startsWith("//") ? callbackUrl : "/";
  return NextResponse.redirect(new URL(target, baseUrl));
}
