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
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useTranslations } from "next-intl";

/**
 * Register page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function RegisterPage() {
  const t = useTranslations("Register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!acceptedTerms) {
      setError(t("mustAcceptTerms"));
      return;
    }
    setError("");

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, display_name: displayName }),
    });

    if (res.ok) {
      const data = await res.json();
      // Exchange token in BFF to set the session cookie
      window.location.href = `/api/auth-exchange?token=${data.token}`;
    } else {
      const errData = await res.json();
      setError(errData.error || t("registrationFailed"));
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

          <Button
            className="w-full"
            variant="outline"
            onClick={() => (window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/auth/login/google`)}
          >
            {t("googleSignUp")}
          </Button>

          <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:block after:border-b after:border-border">
            <span className="relative z-10 px-2 text-muted-foreground">{t("orEmail")}</span>
          </div>

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
                minLength={6}
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

            <Button type="submit" className="w-full" disabled={!acceptedTerms} variant="ghost">
              {t("signUpButton")}
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
