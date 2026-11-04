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
import { App, type URLOpenListenerEvent } from "@capacitor/app";
import { Browser } from "@capacitor/browser";
import type { QueryClient } from "@tanstack/react-query";
import { isNativeApp } from "./platform";
import { setAuthToken } from "./storage";
import { apiClient } from "@/lib/api/client";

export interface NavigationRouter {
  push: (href: string) => void;
  replace: (href: string) => void;
  back: () => void;
}

/**
 * Parses custom scheme URLs (e.g. `iqoqo://auth-exchange?token=XYZ#token=XYZ`)
 * or universal links (`https://iqoqo.cc/item/123`).
 *
 * @param rawUrl - Raw URL string from native launch or appUrlOpen event
 * @returns Parsed internal route path and any extracted auth token
 */
export function parseAppUrl(rawUrl: string): { path: string; token: string | null; code: string | null } {
  try {
    let normalized = rawUrl;
    if (normalized.startsWith("iqoqo://")) {
      normalized = normalized.replace("iqoqo://", "https://app.iqoqo.local/");
    } else if (normalized.startsWith("intent://")) {
      normalized = normalized.replace("intent://", "https://app.iqoqo.local/");
    }

    const parsed = new URL(normalized);
    let token: string | null = parsed.searchParams.get("token");
    const code: string | null = parsed.searchParams.get("code");

    if (!token && parsed.hash) {
      const hashParams = new URLSearchParams(parsed.hash.replace(/^#/, ""));
      token = hashParams.get("token");
    }

    let path = parsed.pathname + (parsed.search || "");
    // Open redirect safety guard: strictly reject protocol-relative '//' paths
    if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\")) {
      path = "/";
    }

    return { path, token, code };
  } catch {
    return { path: "/", token: null, code: null };
  }
}

/**
 * Handle an incoming deep link event, persisting tokens and routing to destination.
 */
export async function handleDeepLink(
  event: URLOpenListenerEvent,
  router: NavigationRouter,
  queryClient?: QueryClient
): Promise<void> {
  const { path, token, code } = parseAppUrl(event.url);

  if (token) {
    await setAuthToken(token);
    if (queryClient) {
      queryClient.clear();
    }
  } else if (code) {
    try {
      const res = await apiClient.post("/auth/exchange", { code });
      const data = res.data;
      const jwt = data?.token || data?.access_token;
      if (jwt) {
        await setAuthToken(jwt);
        if (queryClient) {
          queryClient.clear();
        }
      }
    } catch (err) {
      console.error("Deep link auth exchange error:", err);
    }
  }

  if (path.includes("auth-exchange")) {
    await Browser.close().catch(() => {});
    router.replace("/");
  } else if (path && path !== "/") {
    router.push(path);
  } else if (token || code) {
    router.replace("/");
  }
}

/**
 * Registers deep-link listeners for custom schemes and universal links on native platforms.
 * Handles both cold-start launches and background appUrlOpen transitions.
 *
 * @param router - Navigation router interface
 * @param queryClient - Optional TanStack Query client to clear caches on login
 * @returns Cleanup function to remove native listeners
 */
export function registerDeepLinkHandler(router: NavigationRouter, queryClient?: QueryClient): () => void {
  if (!isNativeApp()) {
    return () => {};
  }

  // Handle cold-start launch URL
  App.getLaunchUrl()
    .then(launch => {
      if (launch && launch.url) {
        handleDeepLink({ url: launch.url }, router, queryClient);
      }
    })
    .catch(() => {});

  // Handle runtime URL openings (while app is backgrounded or open)
  const listenerPromise = App.addListener("appUrlOpen", (event: URLOpenListenerEvent) => {
    handleDeepLink(event, router, queryClient);
  });

  return () => {
    listenerPromise.then(handle => handle.remove()).catch(() => {});
  };
}

/**
 * Registers Android hardware back button handler.
 * Navigates back in history when possible, or minimizes/exits app.
 *
 * @param router - Navigation router interface
 * @returns Cleanup function to remove back button listener
 */
export function registerBackButtonHandler(router: NavigationRouter): () => void {
  if (!isNativeApp()) {
    return () => {};
  }

  const listenerPromise = App.addListener("backButton", ({ canGoBack }) => {
    if (canGoBack) {
      router.back();
    } else {
      App.exitApp();
    }
  });

  return () => {
    listenerPromise.then(handle => handle.remove()).catch(() => {});
  };
}

/**
 * Opens an external URL in the system browser using Capacitor Browser on native platforms,
 * or standard window.open on the web.
 *
 * @param url - Destination URL
 */
export async function openExternalUrl(url: string): Promise<void> {
  if (isNativeApp()) {
    try {
      await Browser.open({ url });
      return;
    } catch (err) {
      console.warn("Failed to open URL in native browser:", err);
    }
  }
  if (typeof window !== "undefined") {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
