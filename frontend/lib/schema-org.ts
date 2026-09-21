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
 * Centralized Schema.org mappings and JSON-LD builders for iqoqo FRBR entities.
 * Conforms to Schema.org standards and Google Rich Results guidelines.
 */

/** Mapping of content types, expression kinds, and media formats to Schema.org types. */
export const SCHEMA_TYPE_MAP: Record<string, string> = {
  text: "Book",
  book: "Book",
  audiobook: "Audiobook",
  music: "MusicAlbum",
  audio: "AudioObject",
  movie: "Movie",
  video: "Movie",
  board_game: "Game",
  cards: "Game",
  video_game: "VideoGame",
  comic_book: "ComicStory",
  graphic_novel: "ComicStory",
  puzzle: "Product",
  jigsaw_puzzle: "Product",
  mechanical_puzzle: "Product",
};

/**
 * Resolves a Schema.org type string based on contentType, expressionKind, and format.
 *
 * @param {string} [contentType] - The FRBR content type (e.g. "text", "board_game").
 * @param {string} [expressionKind] - The expression kind (e.g. "live_performance").
 * @param {string} [format] - The media format (e.g. "comic_book", "audiobook_cd").
 * @returns {string} The canonical Schema.org type.
 */
export function resolveSchemaType(
  contentType?: string | null,
  expressionKind?: string | null,
  format?: string | null
): string {
  const normFormat = (format || "").toLowerCase().trim();
  const normType = (contentType || "").toLowerCase().trim();

  // Check format-specific overrides first
  if (normFormat === "comic_book" || normFormat === "graphic_novel") {
    return "ComicStory";
  }
  if (normFormat.startsWith("audiobook")) {
    return "Audiobook";
  }
  if (normFormat === "video_game") {
    return "VideoGame";
  }

  // Check content type
  if (normType && SCHEMA_TYPE_MAP[normType]) {
    return SCHEMA_TYPE_MAP[normType];
  }

  if (normFormat && SCHEMA_TYPE_MAP[normFormat]) {
    return SCHEMA_TYPE_MAP[normFormat];
  }

  return "CreativeWork";
}

/** Standard 3-letter to 2-letter BCP 47 language mapping for common library catalog codes. */
const ISO_639_2_TO_1: Record<string, string> = {
  eng: "en",
  pol: "pl",
  fra: "fr",
  deu: "de",
  ger: "de",
  spa: "es",
  ita: "it",
  jpn: "ja",
  zho: "zh",
  chi: "zh",
  rus: "ru",
  por: "pt",
  lat: "la",
  gre: "el",
  ell: "el",
};

/**
 * Normalizes a language code for Schema.org `inLanguage`.
 *
 * @param {string} [lang] - Language code (ISO 639-1, 639-2, or name).
 * @returns {string | undefined} Normalized language tag or undefined if missing.
 */
export function resolveInLanguage(lang?: string | null): string | undefined {
  if (!lang) return undefined;
  const trimmed = lang.trim().toLowerCase();
  if (!trimmed) return undefined;

  // Convert 3-letter code if present, otherwise return cleaned 2-letter or standard code
  return ISO_639_2_TO_1[trimmed] || trimmed;
}

/**
 * Maps an iqoqo item collection status to a Schema.org ItemAvailability URI.
 *
 * @param {string} [status] - The collection status (e.g. "owned", "wishlist", "lent").
 * @returns {string} The full Schema.org ItemAvailability URI.
 */
export function mapCollectionStatusToAvailability(status?: string | null): string {
  const norm = (status || "").toLowerCase().trim();
  switch (norm) {
    case "available":
    case "owned":
    case "in_library":
    case "for_sale":
      return "https://schema.org/InStock";
    case "wishlist":
    case "wish_list":
    case "wanted":
    case "ordered":
      return "https://schema.org/PreOrder";
    case "lent":
    case "on_loan":
      return "https://schema.org/LimitedAvailability";
    case "damaged":
    case "lost":
      return "https://schema.org/OutOfStock";
    default:
      return "https://schema.org/InStock";
  }
}

/** Options for creating a Schema.org Offer JSON-LD object. */
export interface OfferOptions {
  status?: string | null;
  price?: string | number | null;
  currency?: string | null;
  condition?: string | null;
  sellerName?: string | null;
}

/**
 * Builds a Schema.org Offer object representing inventory availability.
 *
 * @param {OfferOptions} [options] - Offer configuration options.
 * @returns {Record<string, unknown>} Offer JSON-LD object.
 */
export function buildOfferJsonLd(options?: OfferOptions): Record<string, unknown> {
  const availability = mapCollectionStatusToAvailability(options?.status);
  return {
    "@type": "Offer",
    availability,
    itemCondition: options?.condition || "https://schema.org/UsedCondition",
    price: options?.price !== undefined && options?.price !== null ? String(options.price) : "0",
    priceCurrency: options?.currency || "USD",
    seller: {
      "@type": "Organization",
      name: options?.sellerName || "iqoqo Library",
    },
  };
}

/** Options for generating a Manifestation JSON-LD payload. */
export interface ManifestationJsonLdOptions {
  id: number | string;
  title: string;
  authors?: string[] | string | null;
  coverUrl?: string | null;
  isbn?: string | null;
  publisher?: string | null;
  datePublished?: string | number | null;
  language?: string | null;
  contentType?: string | null;
  expressionKind?: string | null;
  format?: string | null;
  offers?: OfferOptions[];
}

/**
 * Builds a complete Schema.org JSON-LD object for a Manifestation.
 *
 * @param {ManifestationJsonLdOptions} options - Manifestation metadata options.
 * @returns {Record<string, unknown>} Complete JSON-LD object.
 */
export function buildManifestationJsonLd(options: ManifestationJsonLdOptions): Record<string, unknown> {
  const schemaType = resolveSchemaType(options.contentType, options.expressionKind, options.format);
  const resolvedAuthorName = Array.isArray(options.authors)
    ? options.authors[0] || "Unknown Author"
    : options.authors || "Unknown Author";

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": schemaType,
    name: options.title || "Untitled Work",
    author: {
      "@type": "Person",
      name: resolvedAuthorName,
    },
    identifier: options.id,
  };

  if (options.coverUrl) {
    jsonLd.image = options.coverUrl;
  }
  if (options.isbn) {
    jsonLd.isbn = options.isbn;
  }
  if (options.publisher) {
    jsonLd.publisher = options.publisher;
  }
  if (options.datePublished !== undefined && options.datePublished !== null) {
    jsonLd.datePublished = options.datePublished;
  }
  const normalizedLang = resolveInLanguage(options.language);
  if (normalizedLang) {
    jsonLd.inLanguage = normalizedLang;
  }

  if (options.offers && options.offers.length > 0) {
    jsonLd.offers = options.offers.map(offer => buildOfferJsonLd(offer));
  }

  return jsonLd;
}

/** Item reference inside a CollectionPage item list. */
export interface CollectionItemRef {
  id: number | string;
  title: string;
  url?: string;
  contentType?: string | null;
  format?: string | null;
}

/** Options for generating a CollectionPage JSON-LD payload. */
export interface CollectionJsonLdOptions {
  name: string;
  description?: string;
  totalCount: number;
  authorName?: string | null;
  items?: CollectionItemRef[];
}

/**
 * Builds a Schema.org CollectionPage JSON-LD object.
 *
 * @param {CollectionJsonLdOptions} options - Collection metadata options.
 * @returns {Record<string, unknown>} CollectionPage JSON-LD object.
 */
export function buildCollectionJsonLd(options: CollectionJsonLdOptions): Record<string, unknown> {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: options.name,
    description: options.description || `Personal library collection with ${options.totalCount} items`,
    numberOfItems: options.totalCount,
  };

  if (options.authorName) {
    jsonLd.author = {
      "@type": "Person",
      name: options.authorName,
    };
  }

  if (options.items && options.items.length > 0) {
    jsonLd.mainEntity = {
      "@type": "ItemList",
      numberOfItems: options.totalCount,
      itemListElement: options.items.map((item, index) => ({
        "@type": "ListItem",
        position: index + 1,
        item: {
          "@type": resolveSchemaType(item.contentType, undefined, item.format),
          name: item.title,
          ...(item.url ? { url: item.url } : {}),
        },
      })),
    };
  }

  return jsonLd;
}

/** Reference to a manifestation embodied under a work. */
export interface WorkManifestationRef {
  id: number | string;
  title?: string | null;
  isbn?: string | null;
  language?: string | null;
  contentType?: string | null;
  expressionKind?: string | null;
  format?: string | null;
  year?: number | string | null;
}

/** Options for generating a CreativeWork JSON-LD payload for a Work. */
export interface WorkJsonLdOptions {
  id: number | string;
  title: string;
  authors?: string[] | string | null;
  manifestations?: WorkManifestationRef[];
}

/**
 * Builds a Schema.org CreativeWork JSON-LD object with FRBR hierarchy workExample relations.
 *
 * @param {WorkJsonLdOptions} options - Work metadata options.
 * @returns {Record<string, unknown>} CreativeWork JSON-LD object.
 */
export function buildWorkJsonLd(options: WorkJsonLdOptions): Record<string, unknown> {
  const resolvedAuthorName = Array.isArray(options.authors)
    ? options.authors[0] || "Unknown Author"
    : options.authors || "Unknown Author";

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: options.title,
    author: {
      "@type": "Person",
      name: resolvedAuthorName,
    },
    identifier: options.id,
  };

  if (options.manifestations && options.manifestations.length > 0) {
    jsonLd.workExample = options.manifestations.map(m => {
      const type = resolveSchemaType(m.contentType, m.expressionKind, m.format);
      const entry: Record<string, unknown> = {
        "@type": type,
        name: m.title || options.title,
        identifier: m.id,
      };
      if (m.isbn) {
        entry.isbn = m.isbn;
      }
      const lang = resolveInLanguage(m.language);
      if (lang) {
        entry.inLanguage = lang;
      }
      if (m.year !== undefined && m.year !== null) {
        entry.datePublished = m.year;
      }
      return entry;
    });
  }

  return jsonLd;
}

/** Options for generating a CreativeWork JSON-LD payload for an Expression. */
export interface ExpressionJsonLdOptions {
  id: number | string;
  workId: number | string;
  workTitle: string;
  authors?: string[] | string | null;
  language?: string | null;
  contentType?: string | null;
  expressionKind?: string | null;
  manifestations?: WorkManifestationRef[];
}

/**
 * Builds a Schema.org CreativeWork JSON-LD object for an Expression entity.
 *
 * @param {ExpressionJsonLdOptions} options - Expression metadata options.
 * @returns {Record<string, unknown>} CreativeWork JSON-LD object.
 */
export function buildExpressionJsonLd(options: ExpressionJsonLdOptions): Record<string, unknown> {
  const resolvedAuthorName = Array.isArray(options.authors)
    ? options.authors[0] || "Unknown Author"
    : options.authors || "Unknown Author";

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: `${options.workTitle} (${options.language || options.contentType || "Expression"})`,
    author: {
      "@type": "Person",
      name: resolvedAuthorName,
    },
    identifier: options.id,
    isPartOf: {
      "@type": "CreativeWork",
      name: options.workTitle,
      identifier: options.workId,
      url: `/work/${options.workId}`,
    },
  };

  const lang = resolveInLanguage(options.language);
  if (lang) {
    jsonLd.inLanguage = lang;
  }

  if (options.manifestations && options.manifestations.length > 0) {
    jsonLd.workExample = options.manifestations.map(m => {
      const type = resolveSchemaType(
        m.contentType || options.contentType,
        m.expressionKind || options.expressionKind,
        m.format
      );
      const entry: Record<string, unknown> = {
        "@type": type,
        name: m.title || options.workTitle,
        identifier: m.id,
      };
      if (m.isbn) {
        entry.isbn = m.isbn;
      }
      if (m.year !== undefined && m.year !== null) {
        entry.datePublished = m.year;
      }
      return entry;
    });
  }

  return jsonLd;
}

/** Options for generating a ProfilePage JSON-LD payload. */
export interface ProfileJsonLdOptions {
  username: string;
  displayName?: string | null;
  bio?: string | null;
  avatarUrl?: string | null;
  publicItemCount?: number;
}

/**
 * Builds a Schema.org ProfilePage JSON-LD object for a user's public profile.
 *
 * @param {ProfileJsonLdOptions} options - Profile metadata options.
 * @returns {Record<string, unknown>} ProfilePage JSON-LD object.
 */
export function buildProfileJsonLd(options: ProfileJsonLdOptions): Record<string, unknown> {
  const name = options.displayName || options.username;
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    name: `${name}'s Library`,
    mainEntity: {
      "@type": "Person",
      name: name,
      alternateName: options.username,
      ...(options.bio ? { description: options.bio } : {}),
      ...(options.avatarUrl ? { image: options.avatarUrl } : {}),
    },
  };

  if (options.publicItemCount !== undefined) {
    jsonLd.hasPart = {
      "@type": "CollectionPage",
      name: `${name}'s Public Collection`,
      numberOfItems: options.publicItemCount,
    };
  }

  return jsonLd;
}

/**
 * Serializes a JSON-LD value for safe embedding inside an HTML `<script>` tag.
 *
 * JSON-LD payloads are embedded in SSR HTML via `dangerouslySetInnerHTML`. If any
 * catalog or user-controlled string contains `</script>`, `<`, `>`, `&`, or
 * Unicode line/paragraph separators (U+2028, U+2029), the raw `JSON.stringify()`
 * output can break out of the script element and execute stored XSS.
 *
 * This helper performs a second pass over `JSON.stringify()` output, replacing
 * script-breaking characters with their JSON `\uXXXX` escape sequences. JSON
 * parsers decode these escapes back to the original characters, so the resulting
 * payload remains valid JSON-LD with unchanged semantics.
 *
 * @param {unknown} value - The JSON-LD object to serialize.
 * @returns {string} HTML-safe JSON string suitable for `dangerouslySetInnerHTML`.
 */
export function serializeJsonLdForHtml(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}
