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

/**
 * Resolve the Flask API base, matching the rewrite destination the app uses.
 *
 * @returns The API base URL with no trailing slash.
 */
function apiBase(): string {
  return (process.env.FLASK_API_URL || "http://127.0.0.1:5000/api").replace(/\/+$/, "");
}

/**
 * Log out by revoking the token server-side, then clearing the session cookie.
 *
 * This route has to do both. The cookie delete alone is not a logout: the token
 * in it is a JWT that stays cryptographically valid until it expires, so any
 * copy of it -- a proxy log, a shared machine, an exfiltrated cookie -- would
 * keep working after the user believed they had signed out.
 *
 * `POST /api/auth/logout` on the Flask side is what adds the token's `jti` to
 * the blocklist, and it is unreachable from the browser without this call:
 * `next.config.ts` rewrites `/api/:path*` to Flask, but a Next route handler
 * takes precedence over a rewrite, so this file shadows the Flask endpoint for
 * every browser request to that path.
 *
 * @returns {Promise<NextResponse>} A success payload, and a cleared cookie.
 */
export async function POST() {
  const token = (await cookies()).get("iqoqo_session")?.value;

  if (token) {
    try {
      await fetch(`${apiBase()}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
        redirect: "error",
      });
    } catch {
      // Deliberately swallowed. The cookie is cleared either way, because
      // leaving it in place would leave the user signed in against their
      // request -- strictly worse than a token the backend failed to revoke.
      // The backend logs its own failure, so there is a signal to act on.
    }
  }

  const response = NextResponse.json({ success: true, message: "Logged out successfully" });
  response.cookies.delete("iqoqo_session");
  return response;
}
