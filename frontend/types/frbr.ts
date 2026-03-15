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

/** Global Catalog Entry DTO (Returned by /manifestations) */
export interface CatalogEntry extends Manifestation {
  title: string;
  authors: string[];
  cover_path?: string | null;
  cover_status?: string | null;
  user_owns: boolean;
}

export interface Item {
  id: number;
  manifestation_id: number;
  owner_id: string;
  status: ItemStatus;
  meta: Record<string, unknown>;
  added_at?: string;
  updated_at?: string;
  cover_status?: string | null;
  cover_path?: string | null;
  title?: string;
  isbn?: string;
  authors?: string[];
  manifestation_meta?: Record<string, unknown>;
  expression?: Pick<Expression, "id" | "content_type" | "language">;
  work?: Pick<Work, "id" | "title" | "authors" | "meta">;
}

export type ItemStatus = "available" | "lent" | "lost" | "wish_list" | "reading" | "read";

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

export interface DashboardStats {
  works: number;
  expressions: number;
  manifestations: number;
  items: number;
  total_items: number;
  lent_items: number;
  to_read: number;
  items_available: number;
  items_lent: number;
  items_lost: number;
  items_wish_list: number;
  items_reading: number;
  items_read: number;
}

export interface IsbnMeta {
  Title: string;
  Authors: string[];
  Publisher?: string;
  Year?: string;
  Language?: string;
  "ISBN-13"?: string;
}

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
