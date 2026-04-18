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

/** TypeScript types for the FRBR data model used by the iqoqo API. */

/**
 * A distinct intellectual or artistic creation.
 * E.g., The abstract concept of "The Lord of the Rings".
 */
export interface Work {
  id: number;
  title: string;
  authors: string[];
  meta: Record<string, unknown>;
}

/**
 * The intellectual or artistic realization of a work.
 * E.g., The original English text of "The Lord of the Rings", or a French translation.
 */
export interface Expression {
  id: number;
  work_id: number;
  content_type: string;
  language: string;
  format?: string;
  meta?: Record<string, unknown>;
}

/** Additional image attached to a manifestation (e.g., disc, inlay). */
export interface AdditionalImage {
  url: string;
  label: "front" | "back" | "disc" | "inlay" | "box" | "other" | string;
  added_at: string;
}

/**
 * The physical embodiment of an expression of a work.
 * E.g., A specific 2004 paperback edition of "The Lord of the Rings" by a specific publisher.
 */
export interface Manifestation {
  id: number;
  expression_id: number;
  isbn13?: string;
  publisher?: string;
  year?: number;
  cover_url?: string | null;
  owner_count?: number;
  meta: {
    additional_images?: AdditionalImage[];
    format?: "LP" | "45" | "EP" | "CD" | "CD-EP" | "Audiobook" | "Blu-ray" | "DVD" | "VHS" | "Board Game" | string;
    catalog_number?: string;
    pressing_number?: string;
    matrix_number?: string;
    label?: string;
    disc_count?: number;
    track_list?: Array<{
      position: string;
      title: string;
      duration_seconds: number;
    }>;
    // Video-specific
    resolution?: string;
    aspect_ratio?: string;
    video_format?: string;
    audio_formats?: string[];
    region_code?: string;
    run_time_minutes?: number;
    // Game-specific
    min_players?: number;
    max_players?: number;
    playtime_minutes?: number;
    min_age?: number;
    game_mechanics?: string[];
    designer?: string;
    [key: string]: unknown;
  };
}

/** * Global Catalog Entry DTO (Returned by /manifestations).
 * This flattens Work/Expression fields into the Manifestation for UI consumption.
 */
export interface CatalogEntry extends Manifestation {
  title: string;
  authors: string[];
  cover_url?: string | null;
  cover_status?: string | null;
  user_owns: boolean;
}

/**
 * A single exemplar of a manifestation.
 * E.g., The specific dog-eared copy of the 2004 paperback sitting on *your* bookshelf.
 */
export interface Item {
  id: number;
  manifestation_id: number;
  owner_id: string;
  owner_name?: string | null;
  owner_count?: number;
  status: ProgressStatus;
  collection_status: CollectionStatus;
  meta: Record<string, unknown>;
  added_at?: string;
  updated_at?: string;
  cover_status?: string | null;
  cover_url?: string | null;
  title?: string;
  isbn?: string;
  authors?: string[];
  manifestation_meta?: Record<string, unknown>;
  expression?: Pick<Expression, "id" | "content_type" | "language">;
  work?: Pick<Work, "id" | "title" | "authors" | "meta">;
}

/** Physical/Collection status type */
export type CollectionStatus = "available" | "lent" | "lost" | "wish_list" | "ordered" | "damaged";

/** Media-specific progress status type */
export type ProgressStatus =
  | "unread"
  | "reading"
  | "read"
  | "want_to_read"
  | "listening"
  | "listened"
  | "want_to_listen"
  | "watching"
  | "watched"
  | "want_to_watch"
  | "playing"
  | "played";

/** Backward compatible alias for ProgressStatus */
export type ItemStatus = ProgressStatus;

/** Standard media formats used across the app */
export const MEDIA_FORMATS = ["book", "cd", "vinyl", "audio", "video", "boardgame", "puzzle"] as const;
export type MediaFormat = (typeof MEDIA_FORMATS)[number];

/** High-level categories for scanning and manual entry */
export const SCAN_FORMATS = ["book", "audio", "video", "boardgame", "puzzle"] as const;
export type ScanFormat = (typeof SCAN_FORMATS)[number];

/** API Response envelope */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
  meta?: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

/** Dashboard statistics */
export interface DashboardStats {
  works: number;
  expressions: number;
  manifestations: number;
  items: number;
  total_items: number;
  lent_items: number;
  to_read: number;
  items_available: number;
  items_unread: number;
  items_lent: number;
  items_lost: number;
  items_wish_list: number;
  items_reading: number;
  items_read: number;
}

/** Barcode lookup metadata (books, audio, video, games) */
export interface IsbnMeta {
  Title: string;
  Authors: string[];
  title?: string;
  author?: string;
  authors?: string[];
  Publisher?: string;
  Year?: string;
  Language?: string;
  "ISBN-13"?: string;
  Format?: string;
  format?: string;
  barcode?: string;
  isbn?: string;
  identifier?: string;
  cover_url?: string;
  directors?: string[];
  Director?: string[];
  cast?: string[];
  Cast?: string[];
  mechanics?: string[];
  Mechanics?: string[];
  game_mechanics?: string[];
  Description?: string;
  description?: string;
  min_players?: number;
  max_players?: number;
  minPlayers?: number;
  maxPlayers?: number;
  runtime?: number;
  Runtime?: number;
  meta?: Record<string, unknown>;
  already_in_collection?: boolean;
  item_id?: number | null;
  manifestation_id?: number | null;
  discogs_id?: string;
  already_in_db?: boolean;
  candidates?: IsbnMeta[];
}

/** User profile */
export interface UserProfile {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  visibility?: string;
  consents?: Record<string, boolean>;
  roles?: string[];
  permissions?: string[];
  created_at?: string;
}
