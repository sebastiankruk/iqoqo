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
import { MEDIA_HIERARCHY } from "@/types/taxonomy";

/** Type segment keys for the media badge (resolved via i18n in components). */
export type MediaBadgeType = "book" | "movie" | "music" | "audiobook" | "game";

/** Kind segment keys for the media badge (resolved via i18n in components). */
export type MediaBadgeKind = "concert";

/** Resolved segments of the media type badge pill. */
export interface MediaBadgeParts {
  /** Type segment i18n key (book / movie / music / audiobook / game). */
  typeKey: MediaBadgeType;
  /** Kind segment i18n key, present e.g. for live performances ("concert"). */
  kindKey?: MediaBadgeKind;
  /** Carrier format label, language-neutral (e.g. "Vinyl", "Blu-ray", "CD"). */
  formatLabel?: string;
  /** Whether the badge represents audio media (icon / aspect-ratio choice). */
  isAudio: boolean;
}

/** Loose view over the generated taxonomy format entries. */
interface TaxonomyFormatEntry {
  id: string;
  label: string;
}

/** Canonical format id → display label, derived from the generated taxonomy. */
const FORMAT_LABELS: Record<string, string> = {};

/** Canonical format id → media category, derived from the generated taxonomy. */
const FORMAT_CATEGORY: Record<string, string> = {};

for (const [category, def] of Object.entries(MEDIA_HIERARCHY)) {
  for (const f of def.formats as unknown as TaxonomyFormatEntry[]) {
    FORMAT_LABELS[f.id] = f.label;
    FORMAT_CATEGORY[f.id] = category;
  }
}

/**
 * Values that describe a *content type*, not a carrier format. When such a
 * value ends up in a format field (legacy data, type-change fallout) it must
 * never be rendered as the format segment of the badge.
 */
const TYPE_LIKE_VALUES = new Set([
  "text",
  "book",
  "standard",
  "video",
  "movie",
  "film",
  "moving image",
  "music",
  "audio",
  "sound",
  "audiobook",
  "game",
  "video game",
  "board_game",
  "board game",
  "boardgame",
  "puzzle",
  "software",
]);

/**
 * Maps a raw content type string to a badge type key.
 *
 * @param contentType - Raw content type (e.g. "video", "music", "text")
 * @returns The badge type key
 */
function toTypeKey(contentType: string): MediaBadgeType {
  switch (contentType) {
    case "movie":
    case "video":
    case "film":
    case "moving image":
      return "movie";
    case "music":
    case "audio":
    case "sound":
      return "music";
    case "audiobook":
      return "audiobook";
    case "board_game":
    case "board game":
    case "boardgame":
    case "puzzle":
    case "game":
    case "video game":
    case "software":
      return "game";
    default:
      return "book";
  }
}

/**
 * Resolves the segments of the media type badge pill from FRBR data.
 *
 * The pill is composed as ``Type[ / Kind][ / Format]``:
 * - Type comes from the Expression content type (falling back to the format's
 *   category when no content type is available).
 * - Kind reflects the Expression kind (e.g. ``live_performance`` → concert).
 * - Format is the canonical carrier label, shown only when it carries real
 *   information — type-like values (``video``, ``book``), ``unknown_*``
 *   placeholders and segments duplicating the type are suppressed.
 *
 * @param contentType - Expression content type (e.g. "music", "video")
 * @param kind - Expression kind (e.g. "live_performance")
 * @param format - Manifestation carrier format (e.g. "vinyl", "bluray")
 * @returns The resolved badge parts
 */
export function resolveMediaBadge(
  contentType?: string | null,
  kind?: string | null,
  format?: string | null
): MediaBadgeParts {
  const ct = (contentType ?? "").trim().toLowerCase();
  const f = (format ?? "").trim().toLowerCase();

  let typeKey: MediaBadgeType;
  if (ct) {
    typeKey = toTypeKey(ct);
  } else if (f && FORMAT_CATEGORY[f]) {
    // No content type — infer the type segment from the carrier's category.
    typeKey = toTypeKey(FORMAT_CATEGORY[f]);
  } else {
    typeKey = "book";
  }

  const parts: MediaBadgeParts = {
    typeKey,
    isAudio: typeKey === "music" || typeKey === "audiobook",
  };

  if (kind === "live_performance") {
    parts.kindKey = "concert";
  }

  const isInformativeFormat =
    !!f &&
    f !== ct &&
    !TYPE_LIKE_VALUES.has(f) &&
    !f.startsWith("unknown_") &&
    !f.startsWith(`${typeKey}_`) && // e.g. audiobook_cd next to "Audiobook"
    !!FORMAT_LABELS[f];

  if (isInformativeFormat) {
    parts.formatLabel = FORMAT_LABELS[f];
  }

  return parts;
}

/**
 * Composes the media badge label from resolved parts.
 *
 * @param parts - The resolved badge parts
 * @param translate - Translator for the type/kind segment keys
 * @returns The composed label, e.g. "Movie / Concert / Blu-ray"
 */
export function composeMediaBadgeLabel(parts: MediaBadgeParts, translate: (key: string) => string): string {
  const segments = [translate(parts.typeKey)];
  if (parts.kindKey) segments.push(translate(parts.kindKey));
  if (parts.formatLabel) segments.push(parts.formatLabel);
  return segments.join(" / ");
}
