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
import { MEDIA_HIERARCHY, FORMAT_ALIAS_TO_CATEGORY } from "@/types/taxonomy";

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
 * Maps a raw content type or work type string to a badge type key.
 *
 * @param contentTypeOrWorkType - Raw content type (e.g. "video", "music", "text") or work type (e.g. "AudioWork", "GameWork")
 * @returns The badge type key
 */
function toTypeKey(contentTypeOrWorkType: string): MediaBadgeType {
  const normalized = contentTypeOrWorkType.toLowerCase().replace(/[-_\s]/g, "");
  switch (normalized) {
    case "movie":
    case "video":
    case "film":
    case "movingimage":
    case "videowork":
    case "movingimagework":
      return "movie";
    case "music":
    case "audio":
    case "sound":
    case "audiowork":
    case "musicwork":
    case "musicalwork":
      return "music";
    case "audiobook":
    case "audiobookwork":
      return "audiobook";
    case "boardgame":
    case "puzzle":
    case "game":
    case "videogame":
    case "software":
    case "gamework":
    case "threedimensionalobject":
      return "game";
    case "text":
    case "book":
    case "textwork":
    case "standard":
      return "book";
    default:
      return "book";
  }
}

/** Options or Item-like payload passed into resolveMediaBadge. */
export interface ResolveMediaBadgeOptions {
  contentType?: string | null;
  content_type?: string | null;
  kind?: string | null;
  expression_kind?: string | null;
  format?: string | null;
  workType?: string | null;
  work_type?: string | null;
  mediumType?: string | null;
  medium_type?: string | null;
}

/**
 * Resolves the segments of the media type badge pill from FRBR data.
 *
 * The pill is composed as ``Type[ / Kind][ / Format]``:
 * - Type comes from Expression content_type, Work work_type, or medium_type / format category.
 * - Kind reflects the Expression kind (e.g. ``live_performance`` → concert).
 * - Format is the canonical carrier label, shown only when it carries real
 *   information — type-like values (``video``, ``book``), ``unknown_*``
 *   placeholders and segments duplicating the type are suppressed.
 *
 * @param inputOrContentType - Options object or Expression content type (e.g. "music", "video")
 * @param kindArg - Expression kind (e.g. "live_performance")
 * @param formatArg - Manifestation carrier format (e.g. "vinyl", "bluray")
 * @param workTypeArg - Work type discriminator (e.g. "AudioWork", "GameWork")
 * @param mediumTypeArg - Medium type carrier (e.g. "Vinyl", "Audio")
 * @returns The resolved badge parts
 */
export function resolveMediaBadge(
  inputOrContentType?: string | null | ResolveMediaBadgeOptions,
  kindArg?: string | null,
  formatArg?: string | null,
  workTypeArg?: string | null,
  mediumTypeArg?: string | null
): MediaBadgeParts {
  let contentType: string | null | undefined;
  let kind: string | null | undefined;
  let format: string | null | undefined;
  let workType: string | null | undefined;
  let mediumType: string | null | undefined;

  if (inputOrContentType && typeof inputOrContentType === "object") {
    contentType = inputOrContentType.contentType ?? inputOrContentType.content_type;
    kind = inputOrContentType.kind ?? inputOrContentType.expression_kind;
    format = inputOrContentType.format;
    workType = inputOrContentType.workType ?? inputOrContentType.work_type;
    mediumType = inputOrContentType.mediumType ?? inputOrContentType.medium_type;
  } else {
    contentType = inputOrContentType;
    kind = kindArg;
    format = formatArg;
    workType = workTypeArg;
    mediumType = mediumTypeArg;
  }

  const ct = (contentType ?? "").trim();
  const wt = (workType ?? "").trim();
  const mt = (mediumType ?? "").trim();
  const f = (format ?? "").trim().toLowerCase() || mt.toLowerCase();

  let typeKey: MediaBadgeType;
  if (ct) {
    typeKey = toTypeKey(ct);
  } else if (wt) {
    typeKey = toTypeKey(wt);
  } else if (
    mt &&
    (FORMAT_CATEGORY[mt.toLowerCase()] ||
      FORMAT_ALIAS_TO_CATEGORY[mt.toLowerCase()] ||
      TYPE_LIKE_VALUES.has(mt.toLowerCase()))
  ) {
    const resolvedCat =
      FORMAT_CATEGORY[mt.toLowerCase()] || FORMAT_ALIAS_TO_CATEGORY[mt.toLowerCase()] || mt.toLowerCase();
    typeKey = toTypeKey(resolvedCat);
  } else if (f && (FORMAT_CATEGORY[f] || FORMAT_ALIAS_TO_CATEGORY[f] || TYPE_LIKE_VALUES.has(f))) {
    const resolvedCat = FORMAT_CATEGORY[f] || FORMAT_ALIAS_TO_CATEGORY[f] || f;
    typeKey = toTypeKey(resolvedCat);
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
    f !== ct.toLowerCase() &&
    !TYPE_LIKE_VALUES.has(f) &&
    !f.startsWith("unknown_") &&
    !f.startsWith(`${typeKey}_`) && // e.g. audiobook_cd next to "Audiobook"
    !!(FORMAT_LABELS[f] || FORMAT_LABELS[mt.toLowerCase()]);

  if (isInformativeFormat) {
    parts.formatLabel = FORMAT_LABELS[f] || FORMAT_LABELS[mt.toLowerCase()];
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
