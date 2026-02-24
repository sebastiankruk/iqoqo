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
  owner_id: string;
  status: ItemStatus;
  meta: Record<string, unknown>;
  added_at?: string;
  // Joined fields from the API
  title?: string;
  isbn?: string;
  authors?: string[];
  manifestation_meta?: Record<string, unknown>;
  expression?: Pick<Expression, "id" | "content_type" | "language">;
  work?: Pick<Work, "id" | "title" | "authors" | "meta">;
}

/** Item status values as stored in the database. */
export type ItemStatus = "available" | "lent" | "lost" | "wish_list" | "reading" | "read";

/** Standardised API envelope returned by every Flask endpoint. */
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
