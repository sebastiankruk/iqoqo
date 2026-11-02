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

import { useState, useEffect } from "react";
import { isNativeApp } from "@/lib/capacitor/platform";
import { getInstanceUrl } from "@/lib/capacitor/storage";
import { hideSplashScreen } from "@/lib/capacitor/splash";
import { ServerSelector } from "./server-selector";
import { Loader2 } from "lucide-react";

/**
 * Fullscreen onboarding container rendering the server selector for mobile clients.
 */
export function OnboardingScreen({ onConnected }: { onConnected: (instanceUrl: string) => void }) {
  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center px-4 py-8">
      <div className="w-full max-w-md">
        <ServerSelector onConnected={onConnected} />
      </div>
    </div>
  );
}

/**
 * Guard component that renders the initial server setup screen on native mobile
 * devices if no instance URL has been configured yet.
 */
export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(() => isNativeApp());
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  useEffect(() => {
    let mounted = true;

    if (!isNativeApp()) {
      return;
    }

    const checkInstance = async () => {
      try {
        const url = await getInstanceUrl();
        if (mounted) {
          if (!url) {
            setNeedsOnboarding(true);
          } else {
            setNeedsOnboarding(false);
          }
          setChecking(false);
          await hideSplashScreen();
        }
      } catch {
        if (mounted) {
          setNeedsOnboarding(true);
          setChecking(false);
          await hideSplashScreen();
        }
      }
    };

    checkInstance();

    return () => {
      mounted = false;
    };
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (needsOnboarding) {
    return (
      <OnboardingScreen
        onConnected={() => {
          setNeedsOnboarding(false);
        }}
      />
    );
  }

  return <>{children}</>;
}
