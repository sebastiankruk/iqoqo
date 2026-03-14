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

export interface Work {
  id: number;
  title: string;
  authors: string[];
  meta: Record<string, unknown>;
}

export interface Expression {
  id: number;
  work_id: number;
  content_type: string;
  language: string;
  format?: string;
  meta?: Record<string, unknown>;
}

export interface Manifestation {
  id: number;
  expression_id: number;
  isbn13?: string;
  publisher?: string;
  year?: number;
  cover_url?: string;
  meta: Record<string, unknown>;
}

export interface Item {
  id: number;
  manifestation_id: number;
  owner_id: string | null;
  status: ItemStatus;
  meta: Record<string, unknown>;
  added_at?: string;
  /** ISO-8601 timestamp of the last update; falls back to added_at for legacy rows. */
  updated_at?: string;
  /** Cover processing status, flattened from manifestation.meta by the API. */
  cover_status?: string | null;
  /** Relative path to a locally-stored cover image (e.g. /static/covers/…). */
  cover_path?: string | null;
  // Joined fields from the API
  title?: string;
  isbn?: string;
  authors?: string[];
  manifestation_meta?: Record<string, unknown>;
  expression?: Pick<Expression, "id" | "content_type" | "language">;
  work?: Pick<Work, "id" | "title" | "authors" | "meta">;
  // NEW: Indicates if the current user owns this manifestation (when returned from /manifestations)
  user_owns?: boolean;
}

export interface ManifestationListEntry {
  id: number;
  owner_id: null;
  status: "unowned";
  manifestation_id: number;
  isbn?: string;
  title?: string;
  cover_path?: string | null;
  cover_status?: string | null;
  authors?: string[];
  added_at?: string | null;
  updated_at?: string | null;
  user_owns?: boolean;
  // Included to maintain compatibility with components expecting Item
  meta?: Record<string, unknown>;
}

/**
 * Item status values as stored in the database.
 *
 * IMPORTANT: this union must stay in sync with `ITEM_STATUSES` in
 * `app/db/models.py`.  The cross-subsystem contract is enforced by the
 * `test_ontology.py` test suite.
 */
export type ItemStatus = "available" | "lent" | "lost" | "wish_list" | "reading" | "read" | "unowned";

/** Standardized API envelope returned by every Flask endpoint. */
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

/** Dashboard statistics returned by GET /api/stats */
export interface DashboardStats {
  // FRBR entity counts
  works: number;
  expressions: number;
  manifestations: number;
  items: number;
  // UI-friendly aliases
  total_items: number;
  lent_items: number;
  to_read: number;
  // Per-status counts — one key per ItemStatus value (items_available, items_lent, …)
  items_available: number;
  items_lent: number;
  items_lost: number;
  items_wish_list: number;
  items_reading: number;
  items_read: number;
}

/** ISBN lookup response */
export interface IsbnMeta {
  Title: string;
  Authors: string[];
  Publisher?: string;
  Year?: string;
  Language?: string;
  "ISBN-13"?: string;
}

/** User profile data returned by GET /api/profile */
export interface UserProfile {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  visibility?: string;
  consents?: Record<string, boolean>;
  roles?: string[];
  created_at?: string;
}
