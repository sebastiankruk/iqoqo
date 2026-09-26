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
import type { ApiResponse, WishlistItem, WishlistCreateDTO, WishlistUpdateDTO } from "@/types/frbr";

/* ── Query keys ─────────────────────────────────────────────────────────── */

export const wishlistQueryKeys = {
  all: ["wishlist"] as const,
  lists: () => [...wishlistQueryKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) => [...wishlistQueryKeys.lists(), params] as const,
  details: () => [...wishlistQueryKeys.all, "detail"] as const,
  detail: (id: number) => [...wishlistQueryKeys.details(), id] as const,
};

/* ── API client methods ─────────────────────────────────────────────────── */

/** Fetch the authenticated user's wishlist entries. */
export async function fetchWishlist(
  params?: Record<string, unknown>
): Promise<{ data: WishlistItem[]; total: number }> {
  const res = await apiClient.get<ApiResponse<WishlistItem[]>>("/wishlist", {
    params,
  });
  return {
    data: res.data.data ?? [],
    total: res.data.pagination?.total ?? res.data.meta?.total ?? 0,
  };
}

/** Fetch a single wishlist entry by ID. */
export async function fetchWishlistItem(id: number): Promise<WishlistItem> {
  return apiFetch<WishlistItem>(`/wishlist/${id}`);
}

/** Create a new wishlist entry. */
export async function createWishlistItem(dto: WishlistCreateDTO): Promise<WishlistItem> {
  const res = await apiClient.post<ApiResponse<WishlistItem>>("/wishlist", dto);
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Failed to create wishlist entry");
  }
  return res.data.data;
}

/** Update an existing wishlist entry. */
export async function updateWishlistItem(id: number, dto: WishlistUpdateDTO): Promise<WishlistItem> {
  const res = await apiClient.put<ApiResponse<WishlistItem>>(`/wishlist/${id}`, dto);
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Failed to update wishlist entry");
  }
  return res.data.data;
}

/** Delete a wishlist entry. */
export async function deleteWishlistItem(id: number): Promise<void> {
  const res = await apiClient.delete<ApiResponse<{ id: number }>>(`/wishlist/${id}`);
  if (!res.data.success) {
    throw new Error(res.data.error ?? "Failed to delete wishlist entry");
  }
}

/* ── React Query hooks ──────────────────────────────────────────────────── */

/** Fetch the authenticated user's wishlist with pagination and filters. */
export function useWishlist(params?: Record<string, unknown>, enabled = true) {
  return useQuery({
    queryKey: wishlistQueryKeys.list(params),
    queryFn: () => fetchWishlist(params),
    enabled,
    staleTime: 5_000,
  });
}

/** Fetch a single wishlist entry by ID. */
export function useWishlistItem(id: number | null) {
  return useQuery({
    queryKey: wishlistQueryKeys.detail(id!),
    queryFn: () => fetchWishlistItem(id!),
    enabled: id !== null && id > 0,
    staleTime: 5_000,
  });
}

/** Create a new wishlist entry. */
export function useCreateWishlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dto: WishlistCreateDTO) => createWishlistItem(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: wishlistQueryKeys.all });
    },
  });
}

/** Update an existing wishlist entry. */
export function useUpdateWishlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dto }: { id: number; dto: WishlistUpdateDTO }) => updateWishlistItem(id, dto),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: wishlistQueryKeys.all });
      queryClient.invalidateQueries({
        queryKey: wishlistQueryKeys.detail(variables.id),
      });
    },
  });
}

/** Delete a wishlist entry. */
export function useDeleteWishlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteWishlistItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: wishlistQueryKeys.all });
    },
  });
}
