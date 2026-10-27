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

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useTranslations } from "next-intl";
import { useAuthProviders } from "@/hooks/use-auth-providers";

/**
 * Login page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  );
}

/**
 * LoginPageContent component.
 *
 * @returns {JSX.Element} The login page content component.
 */
function LoginPageContent() {
  const t = useTranslations("Login");
  const router = useRouter();
  const { data: providers } = useAuthProviders();
  const isGoogleEnabled = providers?.google ?? false;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("error");
  let errorMessage: string | null = null;
  if (errorCode) {
    try {
      const translated = t(errorCode);
      // next-intl may return the key itself (truthy) when no translation exists;
      // compare against the key to detect a missing translation reliably.
      errorMessage = translated !== errorCode ? translated : `Error: ${errorCode}`;
    } catch {
      errorMessage = `Error: ${errorCode}`;
    }
  }

  /**
   * Handles the local login process.
   *
   * @param {React.FormEvent} e - The form event.
   */
  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsLoading(true);

    try {
      const payload: Record<string, string> = { email, password };
      if (mfaRequired && otpCode.trim()) {
        payload.otp_code = otpCode.trim();
      }

      const res = await fetch(`/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        if (data.mfa_required) {
          setMfaRequired(true);
          return;
        }

        const callbackUrl = searchParams.get("callbackUrl") || searchParams.get("redirect") || "";
        // Exchange token in BFF via POST body — sets httpOnly session cookie
        const exchangeRes = await fetch(`/api/auth-exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: data.token, callbackUrl }),
        });
        if (exchangeRes?.ok) {
          const result = await exchangeRes.json().catch(() => ({}));
          router.push(result.redirectUrl || callbackUrl || "/");
        } else {
          router.push(callbackUrl || "/");
        }
      } else {
        setFormError(data?.error || (mfaRequired ? t("invalidOtp") : t("loginFailed")));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-4 rounded-xl border p-6 shadow-sm bg-card text-card-foreground">
          {mfaRequired ? (
            <>
              <h1 className="text-2xl font-bold">{t("twoFactorTitle")}</h1>
              <p className="text-sm text-muted-foreground">{t("twoFactorDescription")}</p>
              {formError && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">{formError}</div>
              )}
              <form onSubmit={handleLocalLogin} className="space-y-4">
                <input
                  type="text"
                  name="otpCode"
                  autoComplete="one-time-code"
                  placeholder={t("otpPlaceholder")}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={otpCode}
                  onChange={e => setOtpCode(e.target.value)}
                  autoFocus
                />
                <Button type="submit" className="w-full" disabled={isLoading || !otpCode.trim()}>
                  {isLoading ? "..." : t("verifyButton")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    setMfaRequired(false);
                    setOtpCode("");
                    setFormError(null);
                  }}
                >
                  {t("cancel")}
                </Button>
              </form>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold">{t("title")}</h1>
              {errorMessage && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">{errorMessage}</div>
              )}
              {formError && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">{formError}</div>
              )}
              {isGoogleEnabled && (
                <>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => {
                      const callbackUrl = searchParams.get("callbackUrl") || searchParams.get("redirect") || "";
                      const cbQuery = callbackUrl ? `?callbackUrl=${encodeURIComponent(callbackUrl)}` : "";
                      // OAuth flow requires full page navigation to API endpoint
                      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
                      window.location.href = `/api/auth/login/google${cbQuery}`;
                    }}
                  >
                    {t("googleSignIn")}
                  </Button>
                  <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:block after:border-b after:border-border">
                    <span className="relative z-10 px-2 text-muted-foreground">{t("or")}</span>
                  </div>
                </>
              )}
              <form onSubmit={handleLocalLogin} className="space-y-4">
                <input
                  type="email"
                  name="email"
                  autoComplete="email"
                  placeholder={t("emailPlaceholder")}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
                <input
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  placeholder={t("passwordPlaceholder")}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
                <Button type="submit" className="w-full" variant="ghost" disabled={isLoading}>
                  {isLoading ? "..." : t("signInButton")}
                </Button>

                <div className="text-center text-sm pt-4">
                  {t("noAccount")}
                  <Link href="/register" className="underline underline-offset-4 hover:text-primary">
                    {t("signUp")}
                  </Link>
                </div>
              </form>
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
