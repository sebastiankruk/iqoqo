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

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Shield, ExternalLink, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";

/**
 * Checks whether the current environment is running inside a native Capacitor platform.
 *
 * @returns True if running inside iOS or Android native Capacitor WebView.
 */
function isNativeApp(): boolean {
  if (typeof window === "undefined") return false;
  const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean; getPlatform?: () => string } })
    .Capacitor;
  if (!cap) return false;
  if (typeof cap.isNativePlatform === "function") return cap.isNativePlatform();
  const platform = cap.getPlatform?.();
  return platform === "android" || platform === "ios";
}

/**
 * Admin section layout providing native Capacitor platform exclusion.
 * On native mobile builds, guards /admin/* and offers a 1-tap redirect to the system browser.
 *
 * @param props - Layout props containing child routes.
 * @returns The rendered layout.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [native, setNative] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNative(isNativeApp());
    setMounted(true);
  }, []);

  const handleOpenInBrowser = async () => {
    if (typeof window === "undefined") return;
    const currentUrl = window.location.href;
    const cap = (
      window as unknown as {
        Capacitor?: { Plugins?: { Browser?: { open: (opts: { url: string }) => Promise<void> } } };
      }
    ).Capacitor;

    if (cap?.Plugins?.Browser?.open) {
      try {
        await cap.Plugins.Browser.open({ url: currentUrl });
        return;
      } catch {
        // Fallback to window.open
      }
    }
    window.open(currentUrl, "_system");
  };

  if (!mounted) {
    return <>{children}</>;
  }

  if (native) {
    return (
      <div className="min-h-screen flex flex-col bg-background text-foreground">
        <Navbar />
        <main className="flex-1 max-w-lg w-full mx-auto px-4 py-16 flex flex-col items-center justify-center text-center">
          <div className="h-16 w-16 rounded-full bg-accent/10 flex items-center justify-center mb-6">
            <Shield className="h-8 w-8 text-accent" />
          </div>
          <h1 className="text-2xl font-serif font-bold tracking-tight mb-2">Admin Console</h1>
          <p className="text-muted-foreground mb-8 text-sm leading-relaxed">
            Instance administration and configuration are managed via the web browser. Open the admin console in your
            external browser to continue.
          </p>
          <div className="flex flex-col gap-3 w-full">
            <Button onClick={handleOpenInBrowser} className="gap-2 w-full">
              <ExternalLink className="h-4 w-4" />
              Open Admin in External Browser
            </Button>
            <Button variant="ghost" asChild className="gap-2 w-full">
              <Link href="/">
                <ArrowLeft className="h-4 w-4" />
                Return to Library
              </Link>
            </Button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return <>{children}</>;
}
