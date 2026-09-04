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
 * Handle GET requests to exchange a short-lived token for a session cookie.
 *
 * @param request - The incoming Next.js request
 * @returns {Promise<NextResponse>} The Next.js response redirecting to the dashboard
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const { searchParams } = url;
  const token = searchParams.get("token");

  // Determine host and protocol dynamically from incoming reverse-proxy headers or request URL
  const forwardedHost = request.headers.get("x-forwarded-host") || request.headers.get("host") || url.host;
  const forwardedProto =
    request.headers.get("x-forwarded-proto") || (url.protocol.startsWith("https") ? "https" : "http");
  const isHttps = forwardedProto === "https";

  const baseUrl = `${forwardedProto}://${forwardedHost}`;

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
