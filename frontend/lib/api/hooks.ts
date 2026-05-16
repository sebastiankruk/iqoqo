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

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, apiFetch } from "./client";
import type { Item, CatalogEntry, DashboardStats, IsbnMeta, ApiResponse, UserProfile, WorkShelfEntry, ExpressionShelfEntry, WorkPartEntry } from "@/types/frbr";

/* ── Query keys ─────────────────────────────────────────────────────────── */

export const queryKeys = {
  /**
   * Query key for dashboard statistics.
   */
  stats: ["stats"] as const,
  /**
   * Query key for a list of items.
   *
   * @param page - The page number.
   * @param limit - The number of items per page.
   * @param statuses - Optional array of item statuses to filter by.
   * @param query - Optional search query string.
   * @param sort - Optional sort order (updated, added, title, title-desc, author).
   * @param category - Optional category filter.
   * @param formatFilter - Optional format filter.
   * @returns The query key for items.
   */
  items: (
    page = 1,
    limit = 20,
    statuses?: string[],
    query?: string,
    sort?: string,
    category?: string,
    formatFilter?: string
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
  manifestations: (page = 1, limit = 20, query?: string, category?: string, formatFilter?: string) =>
    ["manifestations", page, limit, query ?? "", category ?? "", formatFilter ?? ""] as const,
  manifestation: (id: number) => ["manifestation", id] as const,
  worksShelf: ["works", "shelf"] as const,
  expressionsShelf: ["expressions", "shelf"] as const,
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
 * @returns {import('@tanstack/react-query').UseQueryResult<DashboardStats>} Query result
 */
export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: () => apiFetch<DashboardStats>("/stats"),
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

export function useWorksShelf() {
  return useQuery({
    queryKey: queryKeys.worksShelf,
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<WorkShelfEntry[]>>("/works/shelf");
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useExpressionsShelf() {
  return useQuery({
    queryKey: queryKeys.expressionsShelf,
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ExpressionShelfEntry[]>>("/expressions/shelf");
      return res.data;
    },
    staleTime: 30_000,
  });
}

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
    enabled: id > 0,
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
      qc.invalidateQueries({ queryKey: queryKeys.stats });
      qc.invalidateQueries({ queryKey: ["items"] });
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
    refetchInterval: query => (query.state.data?.cover_status === "pending" ? 3000 : false),
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
      qc.invalidateQueries({ queryKey: queryKeys.stats });
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
      qc.invalidateQueries({ queryKey: queryKeys.stats });
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
          message.includes("Invalid user ID format")
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
