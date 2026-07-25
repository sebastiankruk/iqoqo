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
  container_work_id?: number | null;
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

import type { MediaFormat, ImageType, CollectionStatus, ProgressStatus } from "./taxonomy";
export * from "./taxonomy";

/** Additional image attached to a manifestation (e.g., disc, inlay). */
export interface AdditionalImage {
  url: string;
  label: ImageType | string;
  added_at: string;
}

/**
 * The physical embodiment of an expression of a work.
 * E.g., A specific 2004 paperback edition of "The Lord of the Rings" by a specific publisher.
 */
export interface Manifestation {
  id: number;
  expression_id: number;
  work_id?: number | null;
  container_work_id?: number | null;
  isbn13?: string;
  upc?: string;
  ean?: string;
  publisher?: string;
  year?: number;
  cover_url?: string | null;
  owner_count?: number;
  meta: {
    additional_images?: AdditionalImage[];
    format?: MediaFormat | string;
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
  /** Work ID if available */
  work_id?: number | null;
  /** Item ID if the authenticated user owns this manifestation */
  item_id?: number | null;
  /** Wishlist Item ID (intent ID) if the user has it in wishlist */
  wishlist_item_id?: number | null;
  /** Expression content_type (e.g. "text", "music", "movie", "audiobook", "board_game", "puzzle"). */
  content_type?: string | null;
}

/**
 * A single exemplar of a manifestation.
 * E.g., The specific dog-eared copy of the 2004 paperback sitting on *your* bookshelf.
 */
export interface Item {
  id: number;
  manifestation_id: number;
  owner_id: string;
  is_owner?: boolean;
  owner_name?: string | null;
  owner_count?: number;
  status: ProgressStatus;
  collection_status: CollectionStatus;
  lent_to_user_id?: string | null;
  lent_to_name?: string | null;
  is_borrowed?: boolean;
  is_hidden?: boolean;
  meta: Record<string, unknown>;
  added_at?: string;
  updated_at?: string;
  cover_status?: string | null;
  cover_url?: string | null;
  title?: string;
  isbn?: string;
  authors?: string[];
  tags?: string[];
  genres?: string[];
  publisher?: string;
  manifestation_meta?: Record<string, unknown>;
  expression?: Pick<Expression, "id" | "content_type" | "language">;
  work?: Pick<Work, "id" | "title" | "authors" | "meta" | "container_work_id">;
}

/** Backward compatible alias for ProgressStatus */
export type ItemStatus = ProgressStatus;

/** Work level shelf entry DTO */
export interface WorkShelfEntry {
  work_id: number;
  title: string;
  creators: string[];
  owned_manifestations: Array<{
    manifestation_id: number;
    item_id?: number;
    format: string;
    cover_url?: string | null;
  }>;
  total_items: number;
}

/** Expression level shelf entry DTO */
export interface ExpressionShelfEntry {
  expression_id: number;
  content_type: string;
  language: string;
  work_title: string;
  creators: string[];
  owned_manifestations: Array<{
    manifestation_id: number;
    item_id?: number;
    format: string;
    cover_url?: string | null;
  }>;
  total_items: number;
}

/** Work part (F15 Complex Work) entry DTO */
export interface WorkPartEntry {
  part_work_id: number;
  title: string;
  sequence: number;
  manifestation_id?: number | null;
  cover_url?: string | null;
  item_id?: number | null;
}

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
  pagination?: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
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
  borrowed_items: number;
  to_read: number;
  items_available: number;
  items_want_to_read: number;
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
  public_username?: string;
  bio?: string;
  avatar_url?: string;
  visibility?: string;
  consents?: Record<string, boolean>;
  roles?: string[];
  permissions?: string[];
  created_at?: string;
}

export type UserCollection = {
  id: number;
  name: string;
  parent_id: number | null;
  created_at: string | null;
};

export type TaxonomiesResponse = {
  tags: string[];
  genres: string[];
  collections: string[];
  publishers: string[];
};

export type FacetStatsResponse = {
  category_counts: Record<string, number>;
  format_counts: Record<string, number>;
  status_counts: Record<string, number>;
  collection_counts: Record<string, number>;
  tag_counts: Record<string, number>;
  genre_counts: Record<string, number>;
  publisher_counts: Record<string, number>;
  borrowed_count?: number;
};

/** Custodian metadata escalation request */
export interface EscalationRequest {
  id: number;
  user_id: string;
  user_display_name?: string;
  user_username?: string | null;
  user_avatar_url?: string | null;
  work_id?: number | null;
  expression_id?: number | null;
  manifestation_id?: number | null;
  item_id?: number | null;
  target_type?: string | null;
  field_name: string;
  current_value?: string | null;
  suggested_value: string;
  note?: string | null;
  request_type?: "correction" | "deletion";
  status: "pending" | "accepted" | "rejected" | "duplicate";
  resolved_by?: string | null;
  resolver_display_name?: string | null;
  resolved_at?: string | null;
  resolution_note?: string | null;
  created_at: string;
  updated_at: string;
}
