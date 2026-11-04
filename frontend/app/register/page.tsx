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

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useTranslations } from "next-intl";
import { useAuthProviders } from "@/hooks/use-auth-providers";
import { Browser } from "@capacitor/browser";
import { isNativeApp } from "@/lib/capacitor/platform";
import { getInstanceUrl, setAuthToken } from "@/lib/capacitor/storage";

/**
 * Register page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function RegisterPage() {
  const t = useTranslations("Register");
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: providers } = useAuthProviders();
  const isGoogleEnabled = providers?.google ?? false;
  const isAppleEnabled = providers?.apple ?? false;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [isNative] = useState(() => isNativeApp());

  const handleOAuthRegister = async (provider: "google" | "apple") => {
    if (isNative) {
      const base = (await getInstanceUrl()) || "";
      await Browser.open({ url: `${base}/api/auth/login/${provider}?mobile_origin=capacitor` });
      return;
    }
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/api/auth/login/${provider}`;
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!acceptedTerms) {
      setError(t("mustAcceptTerms"));
      return;
    }
    setError("");
    setIsLoading(true);

    try {
      let registerUrl = "/api/auth/register";
      if (isNativeApp()) {
        const base = (await getInstanceUrl()) || "";
        if (base) registerUrl = `${base}/api/auth/register`;
      }

      const res = await fetch(registerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, display_name: displayName }),
      });

      if (res.ok) {
        const data = await res.json();
        if (isNativeApp()) {
          await setAuthToken(data.token);
          queryClient.clear();
          router.push("/");
          return;
        }

        // Exchange token in BFF via POST body to set the session cookie
        const exchangeRes = await fetch(`/api/auth-exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: data.token }),
        });
        if (exchangeRes.ok) {
          const result = await exchangeRes.json().catch(() => ({}));
          queryClient.clear();
          router.push(result.redirectUrl || "/");
        } else {
          queryClient.clear();
          router.push("/");
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.error || t("registrationFailed"));
      }
    } catch {
      setError(t("registrationFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-6 rounded-xl border p-6 shadow-sm bg-card text-card-foreground">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-bold">{t("title")}</h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>

          {(isGoogleEnabled || isAppleEnabled) && (
            <div className="space-y-2">
              {isGoogleEnabled && (
                <Button className="w-full" variant="outline" onClick={() => handleOAuthRegister("google")}>
                  {t("googleSignUp")}
                </Button>
              )}
              {isAppleEnabled && (
                <Button className="w-full" variant="outline" onClick={() => handleOAuthRegister("apple")}>
                  {t("appleSignUp")}
                </Button>
              )}
              <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:block after:border-b after:border-border">
                <span className="relative z-10 px-2 text-muted-foreground">{t("orEmail")}</span>
              </div>
            </div>
          )}

          {error && <div className="text-sm text-red-500 text-center">{error}</div>}

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <input
                type="text"
                placeholder={t("displayNamePlaceholder")}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <input
                type="email"
                placeholder={t("emailPlaceholder")}
                required
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <input
                type="password"
                placeholder={t("passwordPlaceholder")}
                required
                minLength={8}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>

            <div className="flex items-start space-x-2">
              <input
                type="checkbox"
                id="terms"
                checked={acceptedTerms}
                onChange={e => setAcceptedTerms(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="terms" className="text-xs text-muted-foreground leading-snug">
                {t("agreeTerms")}
                <Link href="/legal/terms" target="_blank" className="underline hover:text-primary">
                  {t("termsOfService")}
                </Link>
                {t("and")}
                <Link href="/legal/privacy" target="_blank" className="underline hover:text-primary">
                  {t("privacyPolicy")}
                </Link>
                .
              </label>
            </div>

            <Button type="submit" className="w-full" disabled={!acceptedTerms || isLoading}>
              {isLoading ? "Signing up..." : t("signUpButton")}
            </Button>
          </form>

          <div className="text-center text-sm">
            {t("alreadyAccount")}
            <Link href="/login" className="underline underline-offset-4 hover:text-primary">
              {t("signIn")}
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
