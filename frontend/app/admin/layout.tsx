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

import { useEffect } from "react";
import { isNativeApp } from "@/lib/capacitor/platform";
import { getInstanceUrl } from "@/lib/capacitor/storage";

/**
 * Admin section layout guard.
 *
 * When the app is running inside a native Capacitor WebView (iOS or Android)
 * admin screens are not part of the mobile shell. Instead the user is
 * redirected to the instance URL opened in an external browser so they can
 * access the full admin panel on the web.
 *
 * @param root0 - Props
 * @param root0.children - Admin page content (rendered on web only).
 * @returns {JSX.Element} Admin content or a "web only" notice.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!isNativeApp()) return;

    void (async () => {
      const { Browser } = await import("@capacitor/browser");
      const url = await getInstanceUrl();
      if (url) {
        await Browser.open({ url: `${url}/admin` });
      }
    })();
  }, []);

  if (isNativeApp()) {
    return (
      <div className="flex h-screen items-center justify-center p-6 text-center">
        <p className="text-muted-foreground">
          Admin features are available in the web version.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
