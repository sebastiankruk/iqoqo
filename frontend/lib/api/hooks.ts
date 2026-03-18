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
import type {
  Item,
  CatalogEntry,
  DashboardStats,
  IsbnMeta,
  ApiResponse,
  UserProfile,
} from "@/types/frbr";

/* ── Query keys ─────────────────────────────────────────────────────────── */

export const queryKeys = {
  stats: ["stats"] as const,
  items: (page = 1, limit = 20, statuses?: string[], query?: string) =>
    ["items", page, limit, statuses?.join(",") ?? "", query ?? ""] as const,
  item: (id: number) => ["item", id] as const,
  isbn: (isbn: string) => ["isbn", isbn] as const,
  manifestations: (page = 1, limit = 20, query?: string) => ["manifestations", page, limit, query ?? ""] as const,
  manifestation: (id: number) => ["manifestation", id] as const,
};

/* ── Dashboard stats ─────────────────────────────────────────────────────── */

/**
 * Fetch dashboard statistics.
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
 * Fetch items list.
 *
 * @param page - Page number
 * @param limit - Items per page
 * @param statuses - Filter by statuses
 * @param query - Search query
 * @param enabled - Whether the query is enabled
 * @returns {import('@tanstack/react-query').UseQueryResult<ApiResponse<Item[]>>} Query result
 */
export function useItems(page = 1, limit = 20, statuses?: string[], query?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.items(page, limit, statuses, query),
    queryFn: async () => {
      const params: Record<string, string | number> = { page, limit };
      if (statuses && statuses.length > 0) {
        params.statuses = statuses.join(",");
      }
      if (query && query.length > 0) {
        params.q = query;
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
 * Fetch manifestations list.
 *
 * @param page - Page number
 * @param limit - Items per page
 * @param query - Search query
 * @param enabled - Whether the query is enabled
 * @returns {import('@tanstack/react-query').UseQueryResult<ApiResponse<CatalogEntry[]>>} Query result
 */
export function useManifestations(page = 1, limit = 20, query?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.manifestations(page, limit, query),
    queryFn: async () => {
      const params: Record<string, string | number> = { page, limit };
      if (query && query.length > 0) {
        params.q = query;
      }
      const res = await apiClient.get<ApiResponse<CatalogEntry[]>>("/manifestations", { params });
      return res.data;
    },
    staleTime: 10_000,
    enabled,
  });
}

/**
 * Fetch a single manifestation.
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

/* ── Single item ─────────────────────────────────────────────────────────── */

/**
 * Fetch a single item.
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
 * Lookup an ISBN.
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
 * Add a new item.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<{ item_id: number }, Error, { isbn: string; metadata?: IsbnMeta }>} Mutation result
 */
export function useAddItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ isbn, metadata }: { isbn: string; metadata?: IsbnMeta }) => {
      const res = await apiClient.post<{ item_id: number }>(`/item/${isbn}`, metadata ?? {});
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.stats });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/**
 * Fetch an item with polling if cover is pending.
 *
 * @param initialData - Initial item data
 * @returns {{ item: Item | undefined }} Object containing the item
 */
export function useManifestationWithPolling(initialData: Item) {
  const { data: item } = useQuery({
    queryKey: queryKeys.item(initialData.id),
    queryFn: () => apiFetch<Item>(`/items/${initialData.id}`),
    initialData: initialData,
    refetchInterval: (query) =>
      query.state.data?.cover_status === 'pending' ? 3000 : false,
  });
  return { item };
}

/**
 * Update an item.
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
 * Delete an item.
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
 * Search an ISBN.
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
 * Regenerate cover for a manifestation.
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
 * Fetch the user profile.
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
        if (message.includes("Token expired") || message.includes("Invalid token") || message.includes("Token missing") || message.includes("Invalid user ID format")) {
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
 * Fetch global statistics.
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
 * Fetch recent manifestations.
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
