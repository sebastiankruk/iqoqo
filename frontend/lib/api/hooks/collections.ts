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

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../client";
import type { ApiResponse, UserCollection } from "@/types/frbr";

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
