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
import { App } from "@capacitor/app";
import { isNativeApp } from "./platform";

/**
 * Register the Android hardware back-button handler.
 *
 * If there is history to navigate back to, goes back one step; otherwise
 * exits the app. A no-op on iOS and web.
 *
 * @param router - Next.js router object (or any object with a `back()` method).
 * @param router.back - Function to navigate back one step.
 */
export function registerBackButtonHandler(router: { back: () => void }): void {
  if (!isNativeApp()) return;

  App.addListener("backButton", ({ canGoBack }) => {
    if (canGoBack) {
      router.back();
    } else {
      void App.exitApp();
    }
  });
}

/**
 * Register the deep-link (appUrlOpen) handler.
 *
 * Parses the incoming URL — including the pathname **and** all query
 * parameters — and pushes it to the Next.js router. This ensures that
 * `iqoqo://auth-exchange?token=<jwt>` and universal-link URLs both
 * route correctly inside the WebView.
 *
 * A no-op on web.
 *
 * @param router - Next.js router object (or any object with a `push()` method).
 * @param router.push - Function to navigate to a path.
 */
export function registerDeepLinkHandler(router: { push: (path: string) => void }): void {
  if (!isNativeApp()) return;

  const handleUrl = (url: string) => {
    try {
      const parsed = new URL(url);
      let fullPath: string;

      // For custom URL schemes (e.g. iqoqo://auth-exchange?token=...), the
      // WHATWG URL parser treats the first segment after `//` as the hostname
      // rather than part of the pathname. Reconstruct the intended path by
      // prepending the hostname as a path segment.
      if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
        const host = parsed.hostname;
        let path = parsed.pathname;
        if (path === "/") {
          path = "";
        }
        fullPath = (host ? `/${host}` : "") + path + parsed.search;
      } else {
        fullPath = parsed.pathname + parsed.search;
      }

      if (fullPath && fullPath !== "/") {
        router.push(fullPath);
      }
    } catch (err) {
      console.error("[DEEP-LINK] Error parsing URL:", err);
    }
  };

  // 1. Warm start listener
  App.addListener("appUrlOpen", ({ url }) => {
    handleUrl(url);
  });

  // 2. Cold start check
  void App.getLaunchUrl().then(result => {
    if (result && result.url) {
      handleUrl(result.url);
    }
  });
}
