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

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useTranslations } from "next-intl";

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    const res = await fetch(`/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.ok) {
      const data = await res.json();
      const callbackUrl = searchParams.get("callbackUrl") || searchParams.get("redirect") || "";
      const callbackQuery = callbackUrl ? `&callbackUrl=${encodeURIComponent(callbackUrl)}` : "";
      // Exchange token in BFF — /api/auth-exchange is a Next.js route handler
      // that sets the httpOnly session cookie then redirects to callbackUrl or /.
      window.location.href = `/api/auth-exchange?token=${data.token}${callbackQuery}`;
    } else {
      alert(t("loginFailed"));
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-4 rounded-xl border p-6 shadow-sm bg-card text-card-foreground">
          <h1 className="text-2xl font-bold">{t("title")}</h1>
          {errorMessage && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">{errorMessage}</div>
          )}
          <Button
            className="w-full"
            variant="outline"
            onClick={() => (window.location.href = `/api/auth/login/google`)}
          >
            {t("googleSignIn")}
          </Button>
          <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:block after:border-b after:border-border">
            <span className="relative z-10 px-2 text-muted-foreground">{t("or")}</span>
          </div>
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
            <Button type="submit" className="w-full" variant="ghost">
              {t("signInButton")}
            </Button>

            <div className="text-center text-sm pt-4">
              {t("noAccount")}
              <Link href="/register" className="underline underline-offset-4 hover:text-primary">
                {t("signUp")}
              </Link>
            </div>
          </form>
        </div>
      </main>
      <Footer />
    </div>
  );
}
