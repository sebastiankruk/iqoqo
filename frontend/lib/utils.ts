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
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { isNativeApp } from "./capacitor/platform";
import { getSyncInstanceUrl } from "./capacitor/storage";

/**
 * Merge class names.
 *
 * @param inputs - Class names to merge
 * @returns {string} Merged class names
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Checks if a given media format string represents an audio-based manifestation.
 *
 * @param format - The format string to check (e.g., "CD", "Vinyl", "Audiobook")
 * @returns {boolean} True if the format is audio-based
 */
export function isAudioMedia(format: string | undefined): boolean {
  if (!format) return false;
  const audioFormats = new Set([
    "audio",
    "cd",
    "vinyl",
    "lp",
    "ep",
    "45",
    "audiobook",
    "cd-ep",
    "sacd",
    "bluray_audio",
    "audiobook_cd",
    "unknown_audio",
  ]);
  return audioFormats.has(format.toLowerCase());
}
/**
 * Extracts a numeric timestamp from metadata for cache-busting.
 *
 * @param meta - Primary metadata object (e.g., manifestation_meta)
 * @param fallbackMeta - Secondary metadata object (e.g., item.meta)
 * @returns {number | ""} The timestamp as number or empty string if not found
 */
export function getCoverTimestamp(
  meta?: Record<string, unknown> | null,
  fallbackMeta?: Record<string, unknown> | null
): number | "" {
  const updatedAt = meta?.["cover_status_updated_at"] ?? fallbackMeta?.["cover_status_updated_at"];
  if (typeof updatedAt !== "string") return "";
  const timestamp = new Date(updatedAt).getTime();
  return Number.isNaN(timestamp) ? "" : timestamp;
}

/**
 * Resolves an API or static resource URL.
 * In a browser context, it defaults to a relative path (e.g., "/api") to stay same-origin.
 * On the server, it prefers an internal FLASK_API_URL absolute path.
 *
 * @param path - The relative path or endpoint (e.g., "/static/covers/123.jpg" or "/items")
 * @param isServer - Set to true when running server-side (e.g., SSR or API routes)
 * @returns {string} The fully resolved URL
 */
export function resolveApiUrl(path: string, isServer = false): string {
  const hasUrlScheme = /^[a-z][a-z\d+.-]*:/i.test(path);
  if (hasUrlScheme) {
    try {
      const url = new URL(path);
      const allowedOrigins = new Set<string>();
      for (const configuredUrl of [process.env.FLASK_API_URL, process.env.NEXT_PUBLIC_API_URL, getSyncInstanceUrl()]) {
        if (!configuredUrl) continue;
        try {
          allowedOrigins.add(new URL(configuredUrl).origin);
        } catch {
          // Relative API paths do not add an external host to the allowlist.
        }
      }
      if (typeof window !== "undefined") allowedOrigins.add(window.location.origin);
      if (isServer) {
        allowedOrigins.add("http://127.0.0.1:5000");
        allowedOrigins.add("http://localhost:5000");
        if (process.env.NEXT_PUBLIC_APP_VERSION) allowedOrigins.add("http://web:5000");
      }
      if (
        (url.protocol === "http:" || url.protocol === "https:") &&
        !url.username &&
        !url.password &&
        allowedOrigins.has(url.origin)
      ) {
        return path;
      }
    } catch {
      return "/api";
    }
    return "/api";
  }

  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  // Native mobile runtime (Capacitor) loads assets from https://localhost or capacitor://localhost.
  // Relative /api paths cannot resolve against local static files, so we prefix with the active instance URL.
  if (isNativeApp()) {
    const instanceUrl = getSyncInstanceUrl();
    if (instanceUrl) {
      const apiPrefix = cleanPath.startsWith("/api") ? cleanPath : `/api${cleanPath}`;
      return `${instanceUrl}${apiPrefix}`;
    }
  }

  // Server-side fetch requires an absolute URL.
  // We prefer FLASK_API_URL (internal) over NEXT_PUBLIC_API_URL (public/relative).
  if (isServer) {
    const apiBase = process.env.FLASK_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000/api";
    let cleanBase = apiBase === "/" ? "" : apiBase.replace(/\/$/, "");
    if (!/^https?:\/\//i.test(cleanBase)) {
      // In Docker, the host is usually 'web'. For local dev it's 127.0.0.1.
      // Default to web:5000 if running in a typical docker setup without FLASK_API_URL.
      // NEXT_PUBLIC_APP_VERSION is set in Docker builds via Dockerfile.prod args.
      const defaultHost = process.env.NEXT_PUBLIC_APP_VERSION ? "http://web:5000" : "http://127.0.0.1:5000";
      cleanBase = `${defaultHost}${cleanBase}`;
    }
    return `${cleanBase}${cleanPath}`;
  }

  // Browser-side (or SSR-rendered for the browser) always prefers relative "/api"
  // to support tunnels/proxies where "localhost" is not resolvable.
  const publicApiUrl = process.env.NEXT_PUBLIC_API_URL || "/api";
  const apiBase = publicApiUrl.startsWith("http") ? "/api" : publicApiUrl;
  const cleanBase = apiBase === "/" ? "" : apiBase.replace(/\/$/, "");

  if (cleanBase && cleanPath.startsWith(cleanBase)) {
    return cleanPath;
  }

  return `${cleanBase}${cleanPath}`;
}

/**
 * Resolves the public base origin for links, shares, and feeds.
 * In a native Capacitor environment (iOS or Android), returns the configured instance
 * URL instead of https://localhost or capacitor://localhost. If no remote instance
 * is configured or if on localhost, falls back to the public canonical frontend URL.
 *
 * @returns {string} Public origin URL without trailing slash.
 */
export function getPublicBaseUrl(): string {
  const defaultPublicUrl = (process.env.NEXT_PUBLIC_FRONTEND_URL || "https://iqoqo.cc").replace(/\/+$/, "");

  if (isNativeApp()) {
    const instanceUrl = getSyncInstanceUrl();
    if (instanceUrl && !instanceUrl.includes("localhost") && !instanceUrl.includes("127.0.0.1")) {
      return instanceUrl.replace(/\/+$/, "");
    }
    return defaultPublicUrl;
  }

  if (typeof window !== "undefined") {
    const isLocalhostOrCapacitor =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.protocol === "capacitor:";
    if (isLocalhostOrCapacitor) {
      const instanceUrl = getSyncInstanceUrl();
      if (instanceUrl && !instanceUrl.includes("localhost") && !instanceUrl.includes("127.0.0.1")) {
        return instanceUrl.replace(/\/+$/, "");
      }
      return defaultPublicUrl;
    }
    return window.location.origin;
  }

  return defaultPublicUrl;
}

/**
 * Resolves a full public URL for share links, feeds, and open-in-browser targets.
 *
 * @param path - Relative or absolute path (e.g. "/share/abc", "/api/public/feed.xml")
 * @returns {string} Fully-qualified public URL.
 */
export function resolvePublicUrl(path: string): string {
  if (/^[a-z][a-z\d+.-]*:/i.test(path)) {
    return path;
  }
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const base = getPublicBaseUrl();
  return `${base}${cleanPath}`;
}

/**
 * Resolves a cover URL using the generic resolveApiUrl logic.
 * Supports optional cache-busting timestamp.
 *
 * @param path - The cover path (e.g., "/static/covers/123.jpg")
 * @param timestamp - Optional timestamp for cache busting
 * @returns {string | undefined} Resolved URL
 */
export function getCoverUrl(path: string | undefined, timestamp?: number | string): string | undefined {
  if (!path) return undefined;
  let coverPath = path;
  if (/^[a-z][a-z\d+.-]*:/i.test(path)) {
    try {
      const parsed = new URL(path);
      const allowedOrigins = new Set<string>();
      for (const configuredUrl of [process.env.FLASK_API_URL, process.env.NEXT_PUBLIC_API_URL, getSyncInstanceUrl()]) {
        if (!configuredUrl) continue;
        try {
          allowedOrigins.add(new URL(configuredUrl).origin);
        } catch {
          // Relative API paths do not add an external host to the allowlist.
        }
      }
      if (!allowedOrigins.has(parsed.origin)) return undefined;
      coverPath = parsed.pathname;
    } catch {
      return undefined;
    }
  }
  if (!/^\/(?:api\/)?static\/covers\/[^/?#]+$/.test(coverPath)) return undefined;
  const url = resolveApiUrl(coverPath);
  if (timestamp) {
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}t=${timestamp}`;
  }
  return url;
}

/**
 * Resolves an avatar image URL.
 * Passes through valid http/https URLs (e.g. Google OAuth avatars on lh3.googleusercontent.com).
 * For relative paths, prefixes with the active instance URL on native mobile platforms.
 *
 * @param src - The avatar source path or URL
 * @returns {string | undefined} Resolved avatar URL or undefined
 */
export function resolveAvatarUrl(src?: string | null): string | undefined {
  if (!src) return undefined;
  if (/^https?:\/\//i.test(src)) {
    return src;
  }
  const cleanPath = src.startsWith("/") ? src : `/${src}`;
  if (isNativeApp()) {
    const instanceUrl = getSyncInstanceUrl();
    if (instanceUrl) {
      const cleanInstance = instanceUrl.replace(/\/$/, "");
      return `${cleanInstance}${cleanPath}`;
    }
  }
  return cleanPath;
}

/**
 * Classifies the cover type based on cover_source metadata.
 *
 * @param meta - The metadata object containing cover_source
 * @returns The cover type: "placeholder" for PIL fallbacks, "llm_gen" for LLM-generated, undefined otherwise
 */
export function classifyCoverType(meta?: Record<string, unknown> | null): "placeholder" | "llm_gen" | undefined {
  const source = meta?.["cover_source"];
  if (source === "fallback_pil") return "placeholder";
  if (typeof source === "string" && source.startsWith("llm_")) return "llm_gen";
  return undefined;
}
