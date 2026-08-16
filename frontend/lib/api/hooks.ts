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
"use client";

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query";
import { apiClient, apiFetch } from "./client";
import { getVelocityInsights, getDistributionInsights } from "./profile";
import type { VelocityPoint, InsightsData } from "@/types/insights";
import type {
  Item,
  CatalogEntry,
  DashboardStats,
  IsbnMeta,
  ApiResponse,
  UserProfile,
  WorkShelfEntry,
  ExpressionShelfEntry,
  WorkPartEntry,
} from "@/types/frbr";

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
  config: ["config"] as const,
};

/**
 * Custom hook to fetch the application configuration.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<{ federation_enabled: boolean; version: string; maintenance_mode: boolean }>} Query result containing the app config
 */
export function useAppConfig() {
  return useQuery({
    queryKey: queryKeys.config,
    queryFn: () => apiFetch<{ federation_enabled: boolean; version: string; maintenance_mode: boolean }>("/config"),
    staleTime: 60 * 60 * 1000,
  });
}

/* ── Dashboard stats ─────────────────────────────────────────────────────── */

/**
 * Custom hook to fetch dashboard statistics.
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns {import('@tanstack/react-query').UseQueryResult<DashboardStats>} Query result
 */
export function useStats(scope: "personal" | "global" = "personal") {
  return useQuery({
    queryKey: queryKeys.stats(scope),
    queryFn: () => apiFetch<DashboardStats>(`/stats?scope=${scope}`),
    staleTime: 30_000,
  });
}

/* ── Items list ──────────────────────────────────────────────────────────── */

/**
 * Custom hook to fetch a list of items.
 *
 * @param page - Page number
 * @param limit - Items per page
 * @param statuses - Filter by statuses
 * @param query - Search query
 * @param sort - Sort order (updated, added, title, title-desc, author)
 * @param enabled - Whether the query is enabled
 * @param category - Category filter
 * @param formatFilter - Format filter
 * @param borrowed - Filter by borrowed status
 * @param missingCover - Filter items missing a cover
 * @param missingId - Filter items missing an external identifier
 * @returns {import('@tanstack/react-query').UseQueryResult<ApiResponse<Item[]>>} Query result
 */
export function useItems(
  page = 1,
  limit = 20,
  statuses?: string[],
  query?: string,
  sort?: string,
  enabled = true,
  category?: string,
  formatFilter?: string,
  borrowed?: boolean,
  missingCover?: boolean,
  missingId?: boolean
) {
  return useQuery({
    queryKey: [
      ...queryKeys.items(page, limit, statuses, query, sort, category, formatFilter),
      borrowed,
      missingCover,
      missingId,
    ],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = { page, limit };
      if (statuses && statuses.length > 0) {
        params.statuses = statuses.join(",");
      }
      if (query && query.length > 0) {
        params.q = query;
      }
      if (sort) {
        params.sort = sort;
      }
      if (category) {
        params.category = category;
      }
      if (formatFilter) {
        params.format = formatFilter;
      }
      if (borrowed) {
        params.borrowed = true;
      }
      if (missingCover) {
        params.missing_cover = true;
      }
      if (missingId) {
        params.missing_id = true;
      }
      const res = await apiClient.get<ApiResponse<Item[]>>("/items", { params });
      return res.data;
    },
    staleTime: 10_000,
    enabled,
  });
}

/**
 * Custom hook to fetch an infinite scrolling list of items.
 *
 * @param limit - Items per page
 * @param statuses - Filter by statuses
 * @param query - Search query
 * @param sort - Sort order (updated, added, title, title-desc, author)
 * @param enabled - Whether the query is enabled
 * @param category - Category filter
 * @param formatFilter - Format filter
 * @param borrowed - Filter by borrowed status
 * @param missingCover - Filter items missing a cover
 * @param missingId - Filter items missing an external identifier
 * @param tags - Filter by tags
 * @param collections - Filter by collections
 * @param genres - Filter by genres
 * @param publishers - Filter by publishers
 * @param includePublic - Whether to include public items
 * @returns {import('@tanstack/react-query').UseInfiniteQueryResult<ApiResponse<Item[]>>} Infinite query result
 */
export function useInfiniteItems(
  limit = 20,
  statuses?: string[],
  query?: string,
  sort?: string,
  enabled = true,
  category?: string,
  formatFilter?: string,
  borrowed?: boolean,
  missingCover?: boolean,
  missingId?: boolean,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  includePublic = false
) {
  return useInfiniteQuery({
    queryKey: [
      ...queryKeys.items(
        1,
        limit,
        statuses,
        query,
        sort,
        category,
        formatFilter,
        tags,
        collections,
        genres,
        publishers
      ),
      "infinite",
      borrowed,
      missingCover,
      missingId,
      includePublic,
    ],
    initialPageParam: 1,
    queryFn: async ({ pageParam = 1 }) => {
      const params: Record<string, string | number | boolean> = { page: pageParam, limit };
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (query && query.length > 0) params.q = query;
      if (sort) params.sort = sort;
      if (category) params.category = category;
      if (formatFilter) params.format = formatFilter;
      if (borrowed) params.borrowed = true;
      if (missingCover) params.missing_cover = true;
      if (missingId) params.missing_id = true;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (includePublic) params.include_public = true;
      const res = await apiClient.get<ApiResponse<Item[]>>("/items", { params });
      return res.data;
    },
    getNextPageParam: lastPage => {
      if (lastPage.meta && lastPage.meta.page < lastPage.meta.pages) {
        return lastPage.meta.page + 1;
      }
      return undefined;
    },
    staleTime: 10_000,
    enabled,
  });
}

/* ── Manifestations list (global catalog) ─────────────────────────────────── */

/**
 * Custom hook to fetch a list of manifestations.
 *
 * @param page - Page number
 * @param limit - Items per page
 * @param query - Search query
 * @param enabled - Whether the query is enabled
 * @param category - Category filter
 * @param formatFilter - Format filter
 * @param missingCover - Filter manifestations missing a cover
 * @param missingId - Filter manifestations missing an external identifier
 * @returns {import('@tanstack/react-query').UseQueryResult<ApiResponse<CatalogEntry[]>>} Query result
 */
export function useManifestations(
  page = 1,
  limit = 20,
  query?: string,
  enabled = true,
  category?: string,
  formatFilter?: string,
  missingCover?: boolean,
  missingId?: boolean
) {
  return useQuery({
    queryKey: [...queryKeys.manifestations(page, limit, query, category, formatFilter), missingCover, missingId],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, limit };
      if (query && query.length > 0) {
        params.q = query;
      }
      if (category) {
        params.category = category;
      }
      if (formatFilter) {
        params.format = formatFilter;
      }
      if (missingCover) {
        (params as Record<string, string | number | boolean>).missing_cover = true;
      }
      if (missingId) {
        (params as Record<string, string | number | boolean>).missing_id = true;
      }
      const res = await apiClient.get<ApiResponse<CatalogEntry[]>>("/manifestations", { params });
      return res.data;
    },
    staleTime: 10_000,
    enabled,
  });
}

/**
 * Custom hook to fetch an infinite scrolling list of manifestations.
 *
 * @param limit - Items per page
 * @param query - Search query
 * @param enabled - Whether the query is enabled
 * @param category - Category filter
 * @param formatFilter - Format filter
 * @param missingCover - Filter manifestations missing a cover
 * @param missingId - Filter manifestations missing an external identifier
 * @param tags - Optional tags filter
 * @param collections - Optional collections filter
 * @param genres - Optional genres filter
 * @param publishers - Optional publishers filter
 * @param statuses - Optional statuses filter
 * @param ownership - Optional ownership filter
 * @returns {import('@tanstack/react-query').UseInfiniteQueryResult<ApiResponse<CatalogEntry[]>>} Infinite query result
 */
export function useInfiniteManifestations(
  limit = 20,
  query?: string,
  enabled = true,
  category?: string,
  formatFilter?: string,
  missingCover?: boolean,
  missingId?: boolean,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  statuses?: string[],
  ownership?: string[]
) {
  return useInfiniteQuery({
    queryKey: [
      ...queryKeys.manifestations(
        1,
        limit,
        query,
        category,
        formatFilter,
        tags,
        collections,
        genres,
        publishers,
        statuses,
        ownership
      ),
      "infinite",
      missingCover,
      missingId,
      ownership,
    ],
    initialPageParam: 1,
    queryFn: async ({ pageParam = 1 }) => {
      const params: Record<string, string | number | boolean> = { page: pageParam, limit };
      if (query && query.length > 0) params.q = query;
      if (category) params.category = category;
      if (formatFilter) params.format = formatFilter;
      if (missingCover) params.missing_cover = true;
      if (missingId) params.missing_id = true;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (ownership && ownership.length > 0) params.ownership = ownership.join(",");
      const res = await apiClient.get<ApiResponse<CatalogEntry[]>>("/manifestations", { params });
      return res.data;
    },
    getNextPageParam: lastPage => {
      if (lastPage.meta && lastPage.meta.page < lastPage.meta.pages) {
        return lastPage.meta.page + 1;
      }
      return undefined;
    },
    staleTime: 10_000,
    enabled,
  });
}

/**
 * Custom hook to fetch a single manifestation by ID.
 *
 * @param id - Manifestation ID
 * @returns {import('@tanstack/react-query').UseQueryResult<CatalogEntry>} Query result
 */
export function useManifestation(id: number) {
  return useQuery({
    queryKey: queryKeys.manifestation(id),
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<CatalogEntry>>(`/manifestations/${id}`);
      return res.data?.data ?? null;
    },
    enabled: id > 0,
  });
}

/* ── Shelves & Views ─────────────────────────────────────────────────────── */

/**
 * React Query hook to fetch the specialized Works Shelf view for the authenticated user.
 * Grouped at the F1 Work level, aggregating manifestations.
 *
 * @param enabled - Whether the query is enabled or not.
 * @param query - Optional search query to filter by work title or creator name.
 * @param category - Optional content_type category filter (e.g. 'text', 'music').
 * @param tags - Optional tags filter.
 * @param collections - Optional collections filter.
 * @param genres - Optional genres filter.
 * @param publishers - Optional publishers filter.
 * @param statuses - Optional statuses filter.
 * @param formats - Optional formats filter.
 * @param ownership - Optional ownership filter.
 * @returns The query result containing the works shelf entries.
 */
export function useWorksShelf(
  enabled = true,
  query?: string,
  category?: string,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  statuses?: string[],
  formats?: string[],
  ownership?: string[]
) {
  return useQuery({
    queryKey: queryKeys.worksShelf(
      query,
      category,
      tags,
      collections,
      genres,
      publishers,
      statuses,
      formats,
      ownership
    ),
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (query && query.length > 0) params.q = query;
      if (category) params.category = category;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (formats && formats.length > 0) params.formats = formats.join(",");
      if (ownership && ownership.length > 0) params.ownership = ownership.join(",");
      const res = await apiClient.get<ApiResponse<WorkShelfEntry[]>>("/works/shelf", { params });
      return res.data;
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * Custom hook to fetch an infinite scrolling list of works shelf entries.
 *
 * @param limit - Items per page
 * @param enabled - Whether the query is enabled
 * @param query - Search query
 * @param category - Category filter
 * @param tags - Tags filter
 * @param collections - Collections filter
 * @param genres - Genres filter
 * @param publishers - Publishers filter
 * @param statuses - Statuses filter
 * @param formats - Formats filter
 * @param ownership - Ownership filter
 * @returns {import('@tanstack/react-query').UseInfiniteQueryResult<ApiResponse<WorkShelfEntry[]>>} Infinite query result
 */
export function useInfiniteWorksShelf(
  limit = 20,
  enabled = true,
  query?: string,
  category?: string,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  statuses?: string[],
  formats?: string[],
  ownership?: string[]
) {
  return useInfiniteQuery({
    queryKey: [
      ...queryKeys.worksShelf(query, category, tags, collections, genres, publishers, statuses, formats, ownership),
      "infinite",
    ],
    initialPageParam: 0,
    queryFn: async ({ pageParam = 0 }) => {
      const params: Record<string, string | number> = { offset: pageParam, limit };
      if (query && query.length > 0) params.q = query;
      if (category) params.category = category;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (formats && formats.length > 0) params.formats = formats.join(",");
      if (ownership && ownership.length > 0) params.ownership = ownership.join(",");
      const res = await apiClient.get<ApiResponse<WorkShelfEntry[]>>("/works/shelf", { params });
      return res.data;
    },
    getNextPageParam: lastPage => {
      if (lastPage.pagination?.has_more) {
        return lastPage.pagination.offset + lastPage.pagination.limit;
      }
      return undefined;
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * React Query hook to fetch the specialized Expressions Shelf view for the authenticated user.
 * Grouped at the F2 Expression level, showing different languages or content types.
 *
 * @param enabled - Whether the query is enabled or not.
 * @param query - Optional search query to filter by work title or creator name.
 * @param category - Optional content_type category filter (e.g. 'text', 'music').
 * @param tags - Optional tags filter.
 * @param collections - Optional collections filter.
 * @param genres - Optional genres filter.
 * @param publishers - Optional publishers filter.
 * @param statuses - Optional statuses filter.
 * @param formats - Optional formats filter.
 * @param ownership - Optional ownership filter.
 * @returns The query result containing the expressions shelf entries.
 */
export function useExpressionsShelf(
  enabled = true,
  query?: string,
  category?: string,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  statuses?: string[],
  formats?: string[],
  ownership?: string[]
) {
  return useQuery({
    queryKey: queryKeys.expressionsShelf(
      query,
      category,
      tags,
      collections,
      genres,
      publishers,
      statuses,
      formats,
      ownership
    ),
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (query && query.length > 0) params.q = query;
      if (category) params.category = category;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (formats && formats.length > 0) params.formats = formats.join(",");
      if (ownership && ownership.length > 0) params.ownership = ownership.join(",");
      const res = await apiClient.get<ApiResponse<ExpressionShelfEntry[]>>("/expressions/shelf", { params });
      return res.data;
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * Custom hook to fetch an infinite scrolling list of expressions shelf entries.
 *
 * @param limit - Items per page
 * @param enabled - Whether the query is enabled
 * @param query - Search query
 * @param category - Category filter
 * @param tags - Tags filter
 * @param collections - Collections filter
 * @param genres - Genres filter
 * @param publishers - Publishers filter
 * @param statuses - Statuses filter
 * @param formats - Formats filter
 * @param ownership - Ownership filter
 * @returns {import('@tanstack/react-query').UseInfiniteQueryResult<ApiResponse<ExpressionShelfEntry[]>>} Infinite query result
 */
export function useInfiniteExpressionsShelf(
  limit = 20,
  enabled = true,
  query?: string,
  category?: string,
  tags?: string[],
  collections?: string[],
  genres?: string[],
  publishers?: string[],
  statuses?: string[],
  formats?: string[],
  ownership?: string[]
) {
  return useInfiniteQuery({
    queryKey: [
      ...queryKeys.expressionsShelf(
        query,
        category,
        tags,
        collections,
        genres,
        publishers,
        statuses,
        formats,
        ownership
      ),
      "infinite",
    ],
    initialPageParam: 0,
    queryFn: async ({ pageParam = 0 }) => {
      const params: Record<string, string | number> = { offset: pageParam, limit };
      if (query && query.length > 0) params.q = query;
      if (category) params.category = category;
      if (tags && tags.length > 0) params.tags = tags.join(",");
      if (collections && collections.length > 0) params.collections = collections.join(",");
      if (genres && genres.length > 0) params.genres = genres.join(",");
      if (publishers && publishers.length > 0) params.publishers = publishers.join(",");
      if (statuses && statuses.length > 0) params.statuses = statuses.join(",");
      if (formats && formats.length > 0) params.formats = formats.join(",");
      if (ownership && ownership.length > 0) params.ownership = ownership.join(",");
      const res = await apiClient.get<ApiResponse<ExpressionShelfEntry[]>>("/expressions/shelf", { params });
      return res.data;
    },
    getNextPageParam: lastPage => {
      if (lastPage.pagination?.has_more) {
        return lastPage.pagination.offset + lastPage.pagination.limit;
      }
      return undefined;
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * React Query hook to fetch the parts/sequence of a complex work (e.g. book series).
 * Grouped at the F15 Complex Work level.
 *
 * @param workId - The database ID of the container work.
 * @returns The query result containing the work parts.
 */
export function useWorkParts(workId: number) {
  return useQuery({
    queryKey: queryKeys.workParts(workId),
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<WorkPartEntry[]>>(`/works/${workId}/parts`);
      return res.data;
    },
    enabled: !!workId,
  });
}

/* ── Single item ─────────────────────────────────────────────────────────── */

/**
 * Custom hook to fetch a single item by ID.
 *
 * @param id - Item ID
 * @returns {import('@tanstack/react-query').UseQueryResult<Item>} Query result
 */
export function useItem(id: number) {
  return useQuery({
    queryKey: queryKeys.item(id),
    queryFn: () => apiFetch<Item>(`/items/${id}`),
    enabled: id !== 0 && !isNaN(id),
  });
}

/* ── Rest of the hooks ─────────────────────────────────────────────────────── */

/**
 * Custom hook to lookup an ISBN.
 *
 * @param isbn - ISBN string
 * @param enabled - Whether the query is enabled
 * @returns {import('@tanstack/react-query').UseQueryResult<IsbnMeta>} Query result
 */
export function useIsbnLookup(isbn: string, enabled = false) {
  return useQuery({
    queryKey: queryKeys.isbn(isbn),
    queryFn: () => apiFetch<IsbnMeta>(`/isbn/${isbn}`),
    enabled: enabled && isbn.length >= 10,
    retry: false,
    staleTime: Infinity,
  });
}

/**
 * Custom hook to search users by name or email.
 *
 * @param query - The search query
 * @param enabled - Whether the query is enabled
 * @returns {import('@tanstack/react-query').UseQueryResult<UserProfile[]>} Query result
 */
export function useUserSearch(query: string, enabled = false) {
  return useQuery({
    queryKey: ["users", "search", query],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UserProfile[]>>("/profile/users/search", { params: { q: query } });
      return res.data?.data ?? [];
    },
    enabled: enabled && query.trim().length >= 2,
    staleTime: 60_000,
  });
}

/**
 * Custom hook to add a new item.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<{ item_id: number; manifestation_id: number }, Error, { isbn?: string; manifestation_id?: number; metadata?: IsbnMeta }>} Mutation result
 */
export function useAddItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      isbn,
      manifestation_id,
      metadata,
    }: {
      isbn?: string;
      manifestation_id?: number;
      metadata?: IsbnMeta;
    }) => {
      if (manifestation_id) {
        const res = await apiClient.post<ApiResponse<{ item_id: number; manifestation_id: number }>>(
          `/manifestations/${manifestation_id}/add`
        );
        return res.data.data!;
      } else if (isbn) {
        const res = await apiClient.post<ApiResponse<{ item_id: number; manifestation_id: number }>>(
          `/item/${isbn}`,
          metadata ?? {}
        );
        return res.data.data!;
      }
      throw new Error("Either isbn or manifestation_id must be provided");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.stats() });
      qc.invalidateQueries({ queryKey: ["items"] });
      qc.invalidateQueries({ queryKey: ["worksShelf"] });
      qc.invalidateQueries({ queryKey: ["expressionsShelf"] });
    },
  });
}

/**
 * Custom hook to fetch an item with polling, specifically designed to update when the cover status is 'pending'.
 *
 * @param initialData - Initial item data
 * @returns {{ item: Item | undefined }} Object containing the item
 */
export function useManifestationWithPolling(initialData: Item) {
  const { data: item } = useQuery({
    queryKey: queryKeys.item(initialData.id),
    queryFn: () => apiFetch<Item>(`/items/${initialData.id}`),
    initialData: initialData,
    refetchInterval: query => (query.state.data?.cover_status === "pending" ? 10000 : false),
  });
  return { item };
}

type ManualItemPayload = {
  Title: string;
  Authors: string[];
  Format: string;
  ISBN?: string;
  PublicationDate?: string;
  Publisher?: string;
  Description?: string;
  tags?: string[];
  genres?: string[];
};

/**
 * Custom hook to add a new item manually when ISBN is not available.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<ApiResponse<{ item_id: number; manifestation_id: number }>, Error, ManualItemPayload>} Mutation result
 */
export function useAddManualItem() {
  const qc = useQueryClient();
  return useMutation<ApiResponse<{ item_id: number; manifestation_id: number }>, Error, ManualItemPayload>({
    mutationFn: async (metadata: ManualItemPayload) => {
      const res = await apiClient.post<ApiResponse<{ item_id: number; manifestation_id: number }>>(
        "/items/manual",
        metadata
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.stats() });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Custom hook to update an item.
 *
 * @param id - Item ID
 * @returns {import('@tanstack/react-query').UseMutationResult<ApiResponse<{ id: number }>, Error, Partial<Item>>} Mutation result
 */
export function useUpdateItem(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Item>) => {
      const res = await apiClient.put<ApiResponse<{ id: number }>>(`/items/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.item(id) });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Custom hook to delete an item.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<number, Error, number>} Mutation result
 */
export function useDeleteItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/items/${id}`);
      return id;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.stats() });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Custom hook to search for an ISBN.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<IsbnMeta, Error, string>} Mutation result
 */
export function useIsbnSearch() {
  return useMutation({
    mutationFn: async (isbn: string) => {
      return apiFetch<IsbnMeta>(`/isbn/${isbn}`);
    },
  });
}

/**
 * Custom hook to regenerate the cover for a manifestation.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<unknown, Error, number>} Mutation result
 */
export function useRegenerateCover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (manifestationId: number) => {
      const res = await apiClient.post(`/manifestations/${manifestationId}/regenerate-cover`);
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Custom hook to fetch the user profile.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<UserProfile | null>} Query result
 */
export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      try {
        const res = await apiFetch<UserProfile>("/profile/");
        return res;
      } catch (err) {
        const message = err instanceof Error ? err.message : "";
        if (
          message.includes("Token expired") ||
          message.includes("Invalid token") ||
          message.includes("Token missing") ||
          message.includes("Invalid user ID format") ||
          message.includes("User not found")
        ) {
          await fetch("/api/auth/logout", { method: "POST" });
        }
        return null;
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Custom hook to fetch global statistics.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<{ works: number; manifestations: number; items: number; users: number }>} Query result
 */
export function useGlobalStats() {
  return useQuery({
    queryKey: ["globalStats"],
    queryFn: () => apiFetch<{ works: number; manifestations: number; items: number; users: number }>("/stats/global"),
    staleTime: 60_000,
  });
}

/**
 * Custom hook to fetch recent manifestations.
 *
 * @param limit - Maximum number of items
 * @returns {import('@tanstack/react-query').UseQueryResult<CatalogEntry[]>} Query result
 */
export function useRecentManifestations(limit = 10) {
  return useQuery({
    queryKey: ["recentManifestations", limit],
    queryFn: () => apiFetch<CatalogEntry[]>("/manifestations/recent", { limit }),
    staleTime: 30_000,
  });
}

import type { FacetStatsResponse, TaxonomiesResponse, UserCollection } from "@/types/frbr";

/**
 * Custom hook to fetch all global taxonomies.
 *
 * @param {object} [options] - Options for fetching taxonomies.
 * @param {"global" | "user"} [options.scope] - The scope of the taxonomies to fetch. Defaults to 'global'.
 * @param {Record<string, string>} [options.filters] - Additional filters to narrow taxonomy values.
 * @returns {import('@tanstack/react-query').UseQueryResult<TaxonomiesResponse>} The query result
 */
export function useTaxonomies(options?: { scope?: "global" | "user"; filters?: Record<string, string> }) {
  const scope = options?.scope || "global";
  const filters = options?.filters;
  return useQuery({
    queryKey: ["taxonomies", scope, filters],
    queryFn: async () => {
      const params = new URLSearchParams({ scope });
      if (filters) {
        Object.entries(filters).forEach(([k, v]) => {
          if (v) params.set(k, v);
        });
      }
      const res = await apiClient.get<ApiResponse<TaxonomiesResponse>>(`/taxonomies?${params.toString()}`);
      return res.data.data;
    },
    staleTime: 60_000,
  });
}

/**
 * Custom hook to fetch all user collections.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<ApiResponse<UserCollection[]>>} The query result
 */
export function useUserCollections() {
  return useQuery({
    queryKey: ["collections"],
    queryFn: async () => {
      const res = await apiClient.get<{ success: boolean; collections: UserCollection[] }>("/collections");
      return res.data.collections;
    },
    staleTime: 60_000,
  });
}

/**
 * Custom hook to fetch cross-filtered facet counts for the sidebar.
 *
 * @param scope - The scope to fetch stats for ("global" or "user")
 * @param filters - Filter params to narrow counts
 * @param enabled - Whether the query is enabled
 * @returns React Query result with per-facet counts
 */
export function useFacetStats(scope: "global" | "user", filters?: Record<string, string>, enabled = true) {
  return useQuery({
    queryKey: ["facetStats", scope, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("scope", scope);
      if (filters) {
        Object.entries(filters).forEach(([k, v]) => {
          if (v) params.set(k, v);
        });
      }
      const res = await apiClient.get<ApiResponse<FacetStatsResponse>>(`/stats/facets?${params.toString()}`);
      return res.data.data ?? ({} as FacetStatsResponse);
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * Custom hook to fetch which named collections an item belongs to.
 *
 * @param itemId - The item ID
 * @returns React Query result with collection list
 */
export function useItemCollections(itemId: number | null) {
  return useQuery({
    queryKey: ["itemCollections", itemId],
    queryFn: async () => {
      const res = await apiClient.get<
        ApiResponse<{ collections: { id: number; name: string; parent_id: number | null }[] }>
      >(`/items/${itemId}/collections`);
      return res.data.data?.collections ?? [];
    },
    enabled: !!itemId && itemId > 0,
    staleTime: 30_000,
  });
}

/**
 * Custom hook to add an item to a named collection.
 *
 * @returns React Query mutation
 */
export function useAddItemToCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, collectionId }: { itemId: number; collectionId: number }) => {
      return apiClient.post(`/items/${itemId}/collections`, { collection_id: collectionId });
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["itemCollections", variables.itemId] });
      qc.invalidateQueries({ queryKey: ["taxonomies"] });
    },
  });
}

/**
 * Custom hook to remove an item from a named collection.
 *
 * @returns React Query mutation
 */
export function useRemoveItemFromCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, collectionId }: { itemId: number; collectionId: number }) => {
      return apiClient.delete(`/items/${itemId}/collections/${collectionId}`);
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["itemCollections", variables.itemId] });
      qc.invalidateQueries({ queryKey: ["taxonomies"] });
    },
  });
}

import { getWorkIntent, setWorkIntent } from "./intents";

/**
 * Custom hook to fetch a user's intent for a given Conceptual Work (F1).
 *
 * @param workId - Work ID
 * @returns React Query query result for the intent
 */
export function useWorkIntent(workId: number) {
  return useQuery({
    queryKey: ["workIntent", workId],
    queryFn: () => getWorkIntent(workId),
    enabled: !!workId && workId > 0,
    staleTime: 10_000,
  });
}

/**
 * Custom hook to set or update a user's intent for a given Conceptual Work (F1).
 *
 * @returns React Query mutation hook
 */
export function useSetWorkIntent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ workId, status }: { workId: number; status: string | null }) => {
      return setWorkIntent(workId, status);
    },
    onSuccess: (_, variables) => {
      void qc.invalidateQueries({ queryKey: ["workIntent", variables.workId] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
      void qc.invalidateQueries({ queryKey: ["items"] });
      void qc.invalidateQueries({ queryKey: ["worksShelf"] });
      void qc.invalidateQueries({ queryKey: ["expressionsShelf"] });
    },
  });
}

/* ── Reading Roadmap ─────────────────────────────────────────────────────── */

export interface RoadmapItemData {
  id: number;
  work_id: number | null;
  manifestation_id: number | null;
  title: string;
  creator: string;
  position: number;
  status: string;
  target_date: string | null;
  notes: string | null;
  completed_at: string | null;
}

export interface RoadmapData {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  items: RoadmapItemData[];
}

/**
 * Custom hook to fetch all reading roadmaps for the authenticated user.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult} Query result
 */
export function useRoadmaps() {
  return useQuery<RoadmapData[]>({
    queryKey: ["roadmaps"],
    queryFn: async () => {
      const res = await apiClient.get<RoadmapData[]>("/v1/roadmaps");
      return res.data ?? [];
    },
    staleTime: 30_000,
  });
}

/**
 * Custom hook to create a new reading roadmap.
 *
 * @returns Mutation result
 */
export function useCreateRoadmap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ title, description }: { title: string; description?: string }) => {
      const res = await apiClient.post<RoadmapData>("/v1/roadmaps", {
        title,
        description,
      });
      return res.data;
    },
    onSuccess: data => {
      qc.setQueryData(["roadmaps"], (old: RoadmapData[] | undefined) => {
        if (!old) return [data];
        if (old.some(r => r.id === data.id)) return old;
        return [...old, data];
      });
      void qc.invalidateQueries({ queryKey: ["roadmaps"] });
    },
  });
}

/**
 * Custom hook to add an item to a reading roadmap.
 *
 * @returns Mutation result
 */
export function useAddRoadmapItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      roadmapId,
      manifestationId,
      workId,
      notes,
    }: {
      roadmapId: number;
      manifestationId?: number;
      workId?: number;
      notes?: string;
    }) => {
      const res = await apiClient.post<RoadmapItemData>(`/v1/roadmaps/${roadmapId}/items`, {
        manifestation_id: manifestationId,
        work_id: workId,
        notes,
      });
      return res.data;
    },
    onSuccess: (newItem, variables) => {
      qc.setQueryData(["roadmaps"], (old: RoadmapData[] | undefined) => {
        if (!old) return old;
        return old.map(r => {
          if (r.id === variables.roadmapId) {
            const items = r.items ? [...r.items] : [];
            if (!items.some(i => i.id === newItem.id)) {
              items.push(newItem);
            }
            return { ...r, items };
          }
          return r;
        });
      });
      void qc.invalidateQueries({ queryKey: ["roadmaps"] });
    },
  });
}

/**
 * Custom hook to reorder a roadmap item.
 *
 * @returns Mutation result
 */
export function useReorderRoadmapItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, position }: { itemId: number; position: number }) => {
      const res = await apiClient.patch(`/v1/roadmaps/items/${itemId}/position`, {
        position,
      });
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["roadmaps"] });
    },
  });
}

/* ── Lending Lifecycle ───────────────────────────────────────────────────── */

export interface LoanRequestData {
  id: number;
  item_id: number;
  item_title: string;
  requester_id: string;
  requester_name: string;
  status: "pending" | "approved" | "rejected";
  notes: string | null;
  created_at: string;
  resolved_at: string | null;
}

/**
 * Custom hook to fetch pending loan requests (for item owners / admins).
 *
 * @returns Query result
 */
export function useLoanRequests() {
  return useQuery<LoanRequestData[]>({
    queryKey: ["loanRequests"],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<LoanRequestData[]>>("/lending/requests");
      return res.data.data ?? [];
    },
    staleTime: 15_000,
  });
}

/**
 * Custom hook to fetch the current user's loan request status for an item.
 *
 * @param itemId - The item to check loan status for
 * @returns Query result
 */
export function useLoanStatus(itemId: number | null) {
  return useQuery<LoanRequestData | null>({
    queryKey: ["loanStatus", itemId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<LoanRequestData | null>>(`/lending/items/${itemId}/loan-status`);
      return res.data.data ?? null;
    },
    enabled: itemId != null && itemId > 0,
    staleTime: 15_000,
  });
}

/**
 * Custom hook to submit a loan request for an item.
 *
 * @returns Mutation result
 */
export function useRequestLoan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, notes }: { itemId: number; notes?: string }) => {
      const res = await apiClient.post<ApiResponse<LoanRequestData>>(`/lending/items/${itemId}/loan-request`, {
        notes,
      });
      return res.data.data!;
    },
    onSuccess: (_, variables) => {
      void qc.invalidateQueries({ queryKey: ["loanStatus", variables.itemId] });
      void qc.invalidateQueries({ queryKey: ["loanRequests"] });
    },
  });
}

/**
 * Custom hook to approve or reject a loan request.
 *
 * @returns Mutation result
 */
export function useResolveLoan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, action }: { requestId: number; action: "approve" | "reject" }) => {
      const res = await apiClient.patch<ApiResponse<LoanRequestData>>(`/lending/requests/${requestId}`, {
        action,
      });
      return res.data.data!;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["loanRequests"] });
      void qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Custom hook to fetch acquisition velocity insights.
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns Query result
 */
export function useVelocityInsights(scope: "personal" | "global" = "personal") {
  return useQuery<VelocityPoint[]>({
    queryKey: ["insights", "velocity", scope],
    queryFn: () => getVelocityInsights(scope),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Custom hook to fetch distribution insights (content types & formats).
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns Query result
 */
export function useDistributionInsights(scope: "personal" | "global" = "personal") {
  return useQuery<InsightsData>({
    queryKey: ["insights", "distribution", scope],
    queryFn: () => getDistributionInsights(scope),
    staleTime: 5 * 60 * 1000,
  });
}
