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

import { useEffect, useState } from "react";
import { isNativeApp } from "@/lib/capacitor/platform";
import { getInstanceUrl } from "@/lib/capacitor/storage";
import { ServerSelector } from "./server-selector";

interface OnboardingGuardProps {
  children: React.ReactNode;
}

/**
 * Guards the app shell on first native launch.
 *
 * If the app is running inside a Capacitor WebView and no instance URL
 * has been persisted yet, renders the {@link ServerSelector} in place of
 * the rest of the app. Once an instance is configured (or on web), renders
 * children normally.
 *
 * @param props - Component props.
 * @param props.children - The guarded app content.
 * @returns {JSX.Element | null} The guard or the app content.
 */
export function OnboardingGuard({ children }: OnboardingGuardProps) {
  const [ready, setReady] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);

  useEffect(() => {
    /** Check if the native app has a configured instance URL. */
    async function check() {
      if (!isNativeApp()) {
        setReady(true);
        return;
      }
      const url = await getInstanceUrl();
      if (!url) {
        setNeedsSetup(true);
      } else {
        localStorage.setItem("iqoqo_instance_url_sync", url);
      }
      setReady(true);
    }
    void check();
  }, []);

  // While checking, return null — the native splash screen is still shown.
  if (!ready) return null;
  if (needsSetup) return <ServerSelector />;
  return <>{children}</>;
}
