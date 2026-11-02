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

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { isNativeApp } from "@/lib/capacitor/platform";
import { setAuthToken } from "@/lib/capacitor/storage";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Smartphone, ArrowRight } from "lucide-react";

/**
 * Internal content component that inspects query tokens and renders the handoff card.
 *
 * @returns {JSX.Element} The rendered auth exchange content
 */
function AuthExchangeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const [token, setToken] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const [showHandoff, setShowHandoff] = useState(false);

  useEffect(() => {
    let extractedToken: string | null = searchParams.get("token");

    if (!extractedToken && typeof window !== "undefined" && window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      extractedToken = hashParams.get("token");
    }

    const code = searchParams.get("code");
    const isMobileFlow = searchParams.get("mobile") === "1" || searchParams.get("mobile_origin") === "capacitor";

    const processAuth = async () => {
      if (extractedToken) {
        setToken(extractedToken);
        // Clear sensitive token from browser address bar immediately
        if (typeof window !== "undefined") {
          window.history.replaceState(null, "", window.location.pathname + window.location.search);
        }

        if (isNativeApp()) {
          await setAuthToken(extractedToken);
          queryClient.clear();
          router.replace("/");
          return;
        }

        if (isMobileFlow) {
          setShowHandoff(true);
          setIsProcessing(false);
          return;
        }

        // Standard web browser fallback
        await setAuthToken(extractedToken);
        queryClient.clear();
        router.replace("/");
        return;
      }

      if (code) {
        try {
          const res = await fetch(`/api/auth-exchange?code=${encodeURIComponent(code)}`);
          if (res.ok) {
            queryClient.clear();
            const data = await res.json().catch(() => ({}));
            router.replace(data.redirectUrl || "/");
            return;
          }
        } catch {
          // Handled below
        }
      }

      setIsProcessing(false);
    };

    processAuth();
  }, [router, searchParams, queryClient]);

  if (isProcessing) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Signing you in securely...</p>
      </div>
    );
  }

  if (showHandoff && token) {
    const deepLinkUrl = `iqoqo://auth-exchange?token=${encodeURIComponent(token)}`;

    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4 py-8">
        <Card className="w-full max-w-md shadow-lg border-primary/20">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Smartphone className="h-6 w-6 text-primary" />
            </div>
            <CardTitle role="heading" aria-level={2} className="text-2xl font-bold">
              Open in iqoqo
            </CardTitle>
            <CardDescription>Authentication successful! Tap below to return to your iqoqo mobile app.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <a href={deepLinkUrl} className="block w-full">
              <Button className="w-full h-11 text-base font-medium flex items-center justify-center space-x-2">
                <span>Open iqoqo App</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </a>
            <Button
              variant="ghost"
              className="w-full text-muted-foreground"
              onClick={async () => {
                await setAuthToken(token);
                queryClient.clear();
                router.replace("/");
              }}
            >
              Continue in web browser
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center space-y-4 px-4 text-center">
      <p className="text-muted-foreground">Authentication exchange complete or expired.</p>
      <Button onClick={() => router.replace("/login")}>Go to Login</Button>
    </div>
  );
}

/**
 * Client-side OAuth authentication exchange page.
 *
 * @returns {JSX.Element} The rendered auth exchange page
 */
export default function AuthExchangePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar />
      <main className="flex-1 container mx-auto px-4">
        <Suspense
          fallback={
            <div className="flex min-h-[50vh] items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          }
        >
          <AuthExchangeContent />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
