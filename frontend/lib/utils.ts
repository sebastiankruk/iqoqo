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
    "audiobook_cd",
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
  return typeof updatedAt === "string" ? new Date(updatedAt).getTime() : "";
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
  if (path.startsWith("http")) return path;

  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  // Server-side fetch requires an absolute URL.
  // We prefer FLASK_API_URL (internal) over NEXT_PUBLIC_API_URL (public/relative).
  if (isServer) {
    const apiBase = process.env.FLASK_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5002/api";
    let cleanBase = apiBase === "/" ? "" : apiBase.replace(/\/$/, "");
    if (!cleanBase.startsWith("http")) {
      cleanBase = `http://127.0.0.1:5002${cleanBase}`;
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
 * Resolves a cover URL using the generic resolveApiUrl logic.
 * Supports optional cache-busting timestamp.
 *
 * @param path - The cover path (e.g., "/static/covers/123.jpg")
 * @param timestamp - Optional timestamp for cache busting
 * @returns {string | undefined} Resolved URL
 */
export function getCoverUrl(path: string | undefined, timestamp?: number | string): string | undefined {
  if (!path) return undefined;
  const url = resolveApiUrl(path);
  if (timestamp) {
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}t=${timestamp}`;
  }
  return url;
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
