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
/**
 * Route parameter resolution utilities for Next.js static export on Capacitor.
 *
 * In static export mode (`output: "export"`), Next.js exports dynamic routes
 * (`/item/[id]`, `/work/[id]`, etc.) using a static `_placeholder` shell.
 * This hook resolves the live parameter from `useParams()` when running in SSR/web
 * or falls back to resolving from `window.location.pathname` when served inside
 * a native mobile WebView.
 *
 * @module lib/capacitor/route-params
 */
"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export const PLACEHOLDER_PARAM = "_placeholder";

/**
 * Extracts a dynamic route parameter value from a URL pathname.
 *
 * @param pathname - The URL pathname (e.g., "/item/123", "/u/alice")
 * @param paramName - The expected parameter key (e.g., "id", "username")
 * @returns The extracted string value or undefined
 */
export function extractParamFromPathname(pathname: string, paramName: string = "id"): string | undefined {
  if (!pathname) return undefined;

  // Remove leading/trailing slashes and split into segments
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return undefined;

  // The dynamic parameter is typically the final segment (e.g., /item/123 -> 123)
  const lastSegment = segments[segments.length - 1];

  if (lastSegment && lastSegment !== PLACEHOLDER_PARAM) {
    try {
      return decodeURIComponent(lastSegment);
    } catch {
      return lastSegment;
    }
  }

  return undefined;
}

/**
 * Resolves a route parameter from `useParams()`, with fallback to `window.location`
 * when running from a static export placeholder shell in Capacitor WebView.
 *
 * @param paramName - Name of the dynamic parameter (defaults to "id")
 * @returns The resolved parameter value as a string, or undefined if not yet available
 */
export function useResolvedRouteParam(paramName: string = "id"): string | undefined {
  let params: Record<string, string | string[] | undefined> | null = null;
  try {
    params = typeof useParams === "function" ? (useParams() as Record<string, string | string[] | undefined>) : null;
  } catch {
    params = null;
  }
  const rawValue = params?.[paramName];
  const initialParam = Array.isArray(rawValue) ? rawValue[0] : rawValue;

  const isPlaceholderOrMissing = !initialParam || initialParam === PLACEHOLDER_PARAM;

  const [resolvedParam, setResolvedParam] = useState<string | undefined>(() => {
    if (!isPlaceholderOrMissing) return initialParam;
    if (typeof window !== "undefined") {
      const fromPath = extractParamFromPathname(window.location.pathname, paramName);
      if (fromPath) return fromPath;
      const fromQuery = new URLSearchParams(window.location.search).get(paramName);
      if (fromQuery) return fromQuery;
    }
    return undefined;
  });

  useEffect(() => {
    if (!isPlaceholderOrMissing) {
      setResolvedParam(initialParam);
    } else if (typeof window !== "undefined") {
      const fromPath = extractParamFromPathname(window.location.pathname, paramName);
      if (fromPath) {
        setResolvedParam(fromPath);
      } else {
        const fromQuery = new URLSearchParams(window.location.search).get(paramName);
        if (fromQuery) {
          setResolvedParam(fromQuery);
        }
      }
    }
  }, [initialParam, isPlaceholderOrMissing, paramName]);

  return resolvedParam;
}
