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
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

type ExchangeResult = { token: string; callbackUrl: string } | null;

/** Validate deployment hosts before using request forwarding headers. */
function isAllowedHost(hostWithPort: string): boolean {
  const host = hostWithPort.split(":")[0].toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "iqoqo.cc" || host.endsWith(".iqoqo.cc");
}

function resolveFrontendOrigin(request: Request): string {
  const url = new URL(request.url);
  const configuredFrontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL;
  if (configuredFrontendUrl) {
    const configuredUrl = new URL(configuredFrontendUrl);
    if (configuredUrl.protocol === "https:" || configuredUrl.protocol === "http:") {
      return configuredUrl.origin;
    }
  }

  const rawForwardedHost = request.headers.get("x-forwarded-host");
  const rawHost = request.headers.get("host") || "";
  const host =
    rawForwardedHost && isAllowedHost(rawForwardedHost)
      ? rawForwardedHost
      : isAllowedHost(rawHost)
        ? rawHost
        : "localhost:3000";
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const protocol =
    forwardedProto === "https" || forwardedProto === "http"
      ? forwardedProto
      : url.protocol === "https:"
        ? "https"
        : "http";
  return `${protocol}://${host}`;
}

function safeCallbackPath(value: unknown): string {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/";
  }
  try {
    const origin = "https://iqoqo.invalid";
    const target = new URL(value, origin);
    if (target.origin !== origin) return "/";
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return "/";
  }
}

function noStore(response: NextResponse): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
  return response;
}

async function exchangeCode(code: string): Promise<ExchangeResult> {
  const apiBase = (process.env.FLASK_API_URL || "http://127.0.0.1:5000/api").replace(/\/+$/, "");
  const response = await fetch(`${apiBase}/auth/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
    cache: "no-store",
    redirect: "error",
  });
  if (!response.ok) return null;

  const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!payload || typeof payload.token !== "string" || !payload.token) return null;
  return {
    token: payload.token,
    callbackUrl: safeCallbackPath(payload.callbackUrl),
  };
}

function redirectToLogin(origin: string): NextResponse {
  return noStore(NextResponse.redirect(new URL("/login?error=oauth_exchange_failed", origin)));
}

async function setSessionCookie(token: string, isHttps: boolean): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set("iqoqo_session", token, {
    httpOnly: true,
    secure: isHttps,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

/**
 * Google callback lands here with a short-lived, single-use code—not an iQoQo JWT.
 * This server-side handler exchanges it with Flask using POST, then sets the
 * HttpOnly cookie and redirects to a clean URL without the code.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const origin = resolveFrontendOrigin(request);
  if (!code || code.length > 128) return redirectToLogin(origin);

  try {
    const exchanged = await exchangeCode(code);
    if (!exchanged) return redirectToLogin(origin);

    await setSessionCookie(exchanged.token, new URL(origin).protocol === "https:");
    return noStore(NextResponse.redirect(new URL(exchanged.callbackUrl, origin)));
  } catch {
    return redirectToLogin(origin);
  }
}

/**
 * POST supports local login/registration tokens in the request body, and also
 * permits a client-side code exchange. Query-string tokens/codes are never read.
 */
export async function POST(request: Request) {
  let body: Record<string, unknown>;
  try {
    const value = await request.json();
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return noStore(NextResponse.json({ success: false, error: "Invalid request" }, { status: 400 }));
    }
    body = value as Record<string, unknown>;
  } catch {
    return noStore(NextResponse.json({ success: false, error: "Invalid request" }, { status: 400 }));
  }

  if (body.token && body.code) {
    return noStore(NextResponse.json({ success: false, error: "Invalid request" }, { status: 400 }));
  }

  let token = typeof body.token === "string" ? body.token : null;
  let callbackUrl = safeCallbackPath(body.callbackUrl);
  if (typeof body.code === "string") {
    try {
      const exchanged = await exchangeCode(body.code);
      if (!exchanged)
        return noStore(NextResponse.json({ success: false, error: "Invalid or expired code" }, { status: 400 }));
      token = exchanged.token;
      callbackUrl = exchanged.callbackUrl;
    } catch {
      return noStore(NextResponse.json({ success: false, error: "OAuth exchange failed" }, { status: 502 }));
    }
  }

  if (!token || token.length > 8192) {
    return noStore(NextResponse.json({ success: false, error: "Missing token or code" }, { status: 400 }));
  }

  const origin = resolveFrontendOrigin(request);
  await setSessionCookie(token, new URL(origin).protocol === "https:");
  const redirectUrl = new URL(callbackUrl, origin).toString();
  return noStore(NextResponse.json({ success: true, redirectUrl }));
}
