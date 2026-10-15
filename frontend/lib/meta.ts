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
 * Reading fields out of a provider-supplied metadata blob.
 *
 * Metadata arrives from several upstreams with inconsistent casing for the
 * same concept: some write `format`, some `Format`, some `categories`, some
 * `Categories`. Rather than let each component rediscover that with its own
 * chain of `||` fallbacks -- six such chains existed across two files, and a
 * component that forgot one simply rendered a blank field -- read fields
 * through here.
 */

/** Keys the caller will accept, in priority order, for a logical field. */
type KeyChain = readonly string[];

/** Fields this project reads, with every spelling known to occur. */
export const FIELD_CHAINS = {
  format: ["format", "Format"],
  year: ["year", "Year"],
  title: ["title", "Title"],
  author: ["author", "authors", "Author", "Authors"],
  authors: ["authors", "author", "Authors", "Author"],
  description: ["description", "Description"],
  categories: ["categories", "Categories"],
  pages: ["pages", "Pages"],
  tracks: ["tracks", "Tracks"],
  publisher: ["publisher", "label", "Publisher"],

  subtitle: ["subtitle", "Subtitle"],
} as const satisfies Record<string, KeyChain>;

/**
 * Dedicated section keys rendered by specific UI sections (Audio, Video, BoardGame, Puzzle, Identifiers)
 * that must be suppressed from fallback Additional Details.
 */
export const DEDICATED_SECTION_KEYS: readonly string[] = [
  "track_list",
  "tracks",
  "additional_images",
  "imageLinks",
  "barcode",
  "isbn",
  "upc",
  "ean",
  "catalog_number",
  "matrix_number",
  "pressing_number",
  "disc_count",
  "min_players",
  "max_players",
  "playing_time",
  "playtime",
  "min_playtime",
  "max_playtime",
  "mechanics",
  "cast",
  "directors",
  "runtime",
  "piece_count",
  "dimensions",
  "artist",
  "manufacturer",
  "puzzle_type",
  "cover_status",
  "cover_source",
  "cover_url",
  "cover_status_updated_at",
  "local_cover",
  "tags",
  "data_source",
] as const;

/**
 * Check if a raw key matches any known spelling of a field declared in FIELD_CHAINS
 * or dedicated section keys, matched case-insensitively.
 *
 * @param key - The raw metadata key
 * @returns True if the key is a known spelling of a declared or dedicated field
 */
export function isKnownMetaSpelling(key: string): boolean {
  if (!key) return false;
  const lowerKey = key.toLowerCase();
  for (const spellings of Object.values(FIELD_CHAINS)) {
    if ((spellings as readonly string[]).some(s => s.toLowerCase() === lowerKey)) {
      return true;
    }
  }
  for (const s of DEDICATED_SECTION_KEYS) {
    if (s.toLowerCase() === lowerKey) {
      return true;
    }
  }
  return false;
}

/** A logical metadata field this module knows how to read. */
export type MetaField = keyof typeof FIELD_CHAINS;

/**
 * Read the first present, non-empty spelling of a metadata field.
 *
 * Empty strings are skipped rather than returned, because an upstream that
 * writes `"format": ""` should fall through to `"Format"` instead of rendering
 * a blank.
 *
 * @param meta - The metadata object to read from.
 * @param field - The logical field name.
 * @returns The first usable value, or undefined when no spelling carries one.
 */
export function readMeta<T = unknown>(
  meta: Record<string, unknown> | undefined | null,
  field: MetaField
): T | undefined {
  if (!meta) {
    return undefined;
  }
  for (const key of FIELD_CHAINS[field]) {
    const value = meta[key];
    if (value !== undefined && value !== null && value !== "") {
      return value as T;
    }
  }
  return undefined;
}

/**
 * Read the first present, non-empty value among an explicit key list.
 *
 * For a field with no fixed meaning across providers — Work-level `genres`,
 * say, which is not something the shared chain map should encode.
 *
 * @param meta - The metadata object to read from.
 * @param keys - Keys to try, in priority order.
 * @returns The first usable value, or undefined.
 */
export function readMetaChain<T = unknown>(
  meta: Record<string, unknown> | undefined | null,
  keys: KeyChain
): T | undefined {
  if (!meta) {
    return undefined;
  }
  for (const key of keys) {
    const value = meta[key];
    if (value !== undefined && value !== null && value !== "") {
      return value as T;
    }
  }
  return undefined;
}

/**
 * Whether any key in an explicit chain carries a usable value.
 *
 * @param meta - The metadata object to read from.
 * @param keys - Keys to consider.
 * @returns True when readMetaChain() would return something.
 */
export function hasMetaChain(meta: Record<string, unknown> | undefined | null, keys: KeyChain): boolean {
  return readMetaChain(meta, keys) !== undefined;
}

/**
 * Whether any spelling of a field carries a usable value.
 *
 * @param meta - The metadata object to read from.
 * @param field - The logical field name.
 * @returns True when readMeta() would return something.
 */
export function hasMeta(meta: Record<string, unknown> | undefined | null, field: MetaField): boolean {
  return readMeta(meta, field) !== undefined;
}
