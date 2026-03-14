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
};

/* ── Dashboard stats ─────────────────────────────────────────────────────── */

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: () => apiFetch<DashboardStats>("/stats"),
    staleTime: 30_000,
  });
}

/* ── Items list ──────────────────────────────────────────────────────────── */

/**
 * Fetch a paginated list of items, optionally filtered by one or more statuses.
 *
 * Statuses are sent to the API as a comma-separated string so a single query
 * parameter covers multiple values (e.g. `?statuses=reading,wish_list`).
 * Results are returned ordered by most-recently-updated first.
 */
export function useItems(page = 1, limit = 20, statuses?: string[], query?: string) {
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
      return res.data; // Return full envelope so we get meta.total
    },
    staleTime: 10_000,
  });
}

/* ── Single item ─────────────────────────────────────────────────────────── */

export function useItem(id: number) {
  return useQuery({
    queryKey: queryKeys.item(id),
    queryFn: () => apiFetch<Item>(`/items/${id}`),
    enabled: id > 0,
  });
}

/* ── ISBN lookup ─────────────────────────────────────────────────────────── */

export function useIsbnLookup(isbn: string, enabled = false) {
  return useQuery({
    queryKey: queryKeys.isbn(isbn),
    queryFn: () => apiFetch<IsbnMeta>(`/isbn/${isbn}`),
    enabled: enabled && isbn.length >= 10,
    retry: false,
    staleTime: Infinity,
  });
}

/* ── Add item (by ISBN) ──────────────────────────────────────────────────── */

export function useAddItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      isbn,
      metadata,
    }: {
      isbn: string;
      metadata?: IsbnMeta;
    }) => {
      const res = await apiClient.post<{ item_id: number }>(`/item/${isbn}`, metadata ?? {});
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.stats });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/* ── Polling Hook for Async Updates ─────────────────────────────────────── */

export function useManifestationWithPolling(initialData: Item) {
  const { data: item } = useQuery({
    queryKey: queryKeys.item(initialData.id),
    queryFn: () => apiFetch<Item>(`/items/${initialData.id}`),
    initialData: initialData,
    // Automatically polls every 3 seconds ONLY if the status is pending
    refetchInterval: (query) =>
      query.state.data?.cover_status === 'pending' ? 3000 : false,
  });

  // Return it in the same { item } shape the component is currently expecting
  return { item };
}

/* ── Update item ─────────────────────────────────────────────────────────── */

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

/* ── Delete item ─────────────────────────────────────────────────────────── */

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

/* ── Lazy ISBN lookup (triggered on demand) ─────────────────────────────── */

export function useIsbnSearch() {
  return useMutation({
    mutationFn: async (isbn: string) => {
      return apiFetch<IsbnMeta>(`/isbn/${isbn}`);
    },
  });
}

/* ── Regenerate Cover ───────────────────────────────────────────────────── */

export function useRegenerateCover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (manifestationId: number) => {
      const res = await apiClient.post(`/manifestations/${manifestationId}/regenerate-cover`);
      return res.data;
    },
    onSuccess: () => {
      // Ensure the collection list picks up the new cover_status: 'pending' state.
      void qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

/* ── Auth / Profile ──────────────────────────────────────────────────────── */

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      try {
        const res = await apiFetch<UserProfile>("/profile/");
        return res;
      } catch (err) {
        // If the token is expired/invalid, clear the stale httpOnly cookie so
        // the proxy stops treating this browser as "logged in" and redirecting
        // /login → /discover in an infinite loop.
        const message = err instanceof Error ? err.message : "";
        if (message.includes("Token expired") || message.includes("Invalid token") || message.includes("Token missing") || message.includes("Invalid user ID format")) {
          await fetch("/api/auth/logout", { method: "POST" });
        }
        return null;
      }
    },
    retry: false, // Don't retry on 401s
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

/* ── Global instance stats (for landing page) ───────────────────────────────── */
export function useGlobalStats() {
  return useQuery({
    queryKey: ["globalStats"],
    queryFn: () => apiFetch<{ works: number; manifestations: number; items: number; users: number }>("/stats/global"),
    staleTime: 60_000,
  });
}

/* ── Recent manifestations (public landing) ───────────────────────────────── */
export function useRecentManifestations(limit = 10) {
  return useQuery({
    queryKey: ["recentManifestations", limit],
    queryFn: () => apiFetch<Record<string, unknown>[]>("/manifestations/recent", { limit }),
    staleTime: 30_000,
  });
}
