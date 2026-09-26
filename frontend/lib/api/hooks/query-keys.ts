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

/* ── Query keys ─────────────────────────────────────────────────────────── */

export const queryKeys = {
  /**
   * Query key for dashboard statistics.
   *
   * @param scope - Data scope ('personal' | 'global')
   * @returns The query key for dashboard statistics.
   */
  stats: (scope?: "personal" | "global") => (scope ? (["stats", scope] as const) : (["stats"] as const)),
  /**
   * Query key for items.
   *
   * @param page - Page number
   * @param limit - Items per page
   * @param statuses - Filter by statuses
   * @param query - Search query
   * @param sort - Sort order
   * @param category - Category filter
   * @param formatFilter - Format filter
   * @param tags - Tags filter
   * @param collections - Collections filter
   * @param genres - Genres filter
   * @param publishers - Publishers filter
   * @returns The query key for items.
   */
  items: (
    page = 1,
    limit = 20,
    statuses?: string[],
    query?: string,
    sort?: string,
    category?: string,
    formatFilter?: string,
    tags?: string[],
    collections?: string[],
    genres?: string[],
    publishers?: string[]
  ) =>
    [
      "items",
      page,
      limit,
      statuses?.join(",") ?? "",
      query ?? "",
      sort ?? "",
      category ?? "",
      formatFilter ?? "",
      tags?.join(",") ?? "",
      collections?.join(",") ?? "",
      genres?.join(",") ?? "",
      publishers?.join(",") ?? "",
    ] as const,
  /**
   * Query key for a single item.
   *
   * @param id - The ID of the item.
   * @returns {readonly ["item", number]} The query key for a single item.
   */
  item: (id: number) => ["item", id] as const,
  /**
   * Query key for ISBN lookup.
   *
   * @param isbn - The ISBN to look up.
   * @returns {readonly ["isbn", string]} The query key for ISBN lookup.
   */
  isbn: (isbn: string) => ["isbn", isbn] as const,
  manifestations: (
    page = 1,
    limit = 20,
    query?: string,
    category?: string,
    formatFilter?: string,
    tags?: string[],
    collections?: string[],
    genres?: string[],
    publishers?: string[],
    statuses?: string[],
    ownership?: string[]
  ) =>
    [
      "manifestations",
      page,
      limit,
      query ?? "",
      category ?? "",
      formatFilter ?? "",
      tags?.join(",") ?? "",
      collections?.join(",") ?? "",
      genres?.join(",") ?? "",
      publishers?.join(",") ?? "",
      statuses?.join(",") ?? "",
      ownership?.join(",") ?? "",
    ] as const,
  manifestation: (id: number) => ["manifestation", id] as const,
  worksShelf: (
    query?: string,
    category?: string,
    tags?: string[],
    collections?: string[],
    genres?: string[],
    publishers?: string[],
    statuses?: string[],
    formats?: string[],
    ownership?: string[]
  ) =>
    [
      "works",
      "shelf",
      query ?? "",
      category ?? "",
      tags?.join(",") ?? "",
      collections?.join(",") ?? "",
      genres?.join(",") ?? "",
      publishers?.join(",") ?? "",
      statuses?.join(",") ?? "",
      formats?.join(",") ?? "",
      ownership?.join(",") ?? "",
    ] as const,
  expressionsShelf: (
    query?: string,
    category?: string,
    tags?: string[],
    collections?: string[],
    genres?: string[],
    publishers?: string[],
    statuses?: string[],
    formats?: string[],
    ownership?: string[]
  ) =>
    [
      "expressions",
      "shelf",
      query ?? "",
      category ?? "",
      tags?.join(",") ?? "",
      collections?.join(",") ?? "",
      genres?.join(",") ?? "",
      publishers?.join(",") ?? "",
      statuses?.join(",") ?? "",
      formats?.join(",") ?? "",
      ownership?.join(",") ?? "",
    ] as const,
  workParts: (id: number) => ["workParts", id] as const,
  /**
   * Query key for the FRBR tree hierarchy.
   *
   * @param id - The manifestation ID
   * @returns The query key for the FRBR tree
   */
  frbrTree: (id: number) => ["admin", "frbr", "tree", id] as const,
  config: ["config"] as const,
};
