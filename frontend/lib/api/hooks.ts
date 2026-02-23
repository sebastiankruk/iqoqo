"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, apiFetch } from "./client";
import type {
  Item,
  DashboardStats,
  IsbnMeta,
  ApiResponse,
} from "@/types/frbr";

/* ── Query keys ─────────────────────────────────────────────────────────── */

export const queryKeys = {
  stats: ["stats"] as const,
  items: (page = 1, limit = 20) => ["items", page, limit] as const,
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

export function useItems(page = 1, limit = 20) {
  return useQuery({
    queryKey: queryKeys.items(page, limit),
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Item[]>>("/items", {
        params: { page, limit },
      });
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
