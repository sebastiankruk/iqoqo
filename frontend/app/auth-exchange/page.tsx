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
"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isNativeApp } from "@/lib/capacitor/platform";
import { setAuthToken } from "@/lib/capacitor/storage";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Handles the token exchange step after OAuth or local login.
 *
 * - **Native**: stores the JWT in encrypted platform storage (Keychain / EncryptedSharedPreferences)
 *   and navigates to the dashboard.
 * - **Web**: delegates to the existing BFF API route `/api/auth-exchange` which
 *   converts the token into an httpOnly session cookie, then follows the redirect.
 *
 * @returns {JSX.Element} Loading UI while the exchange is processed.
 */
function AuthExchangeHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const queryClient = useQueryClient();

  useEffect(() => {
    /** Exchange the token param for persistent auth (secure storage or cookie). */
    async function handleExchange() {
      if (!token) {
        console.error("[AUTH] Exchange error: Token parameter is missing!");
        router.replace("/login");
        return;
      }

      if (isNativeApp()) {
        try {
          await setAuthToken(token);
          queryClient.clear();
          router.replace("/");
        } catch (err) {
          console.error("[AUTH] SecureStorage error:", err);
        }
      } else {
        // Web: call the BFF route handler which sets the httpOnly cookie.
        const res = await fetch(`/api/auth-exchange?token=${encodeURIComponent(token)}`);
        if (res.redirected) {
          router.replace(new URL(res.url).pathname);
        } else {
          router.replace("/");
        }
      }
    }
    void handleExchange();
  }, [token, router, queryClient]);

  return (
    <div className="flex h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing you in…</p>
    </div>
  );
}

/**
 * Client-side auth exchange page.
 * Works in both web mode and Capacitor static export (unlike API route handlers).
 *
 * @returns {JSX.Element} The auth exchange page.
 */
export default function AuthExchangePage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading…</div>}>
      <AuthExchangeHandler />
    </Suspense>
  );
}
