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
import { queryKeys } from "./query-keys";

/* ── Reading Roadmap ─────────────────────────────────────────────────────── */

export interface RoadmapItemSummary {
  title?: string;
  subtitle?: string;
  creator?: string;
  format?: string;
  edition?: string;
  owner_id?: string;
  condition?: string;
}

export interface RoadmapItemData {
  id: number;
  work_id: number | null;
  expression_id: number | null;
  manifestation_id: number | null;
  item_id: number | null;
  target_type?: "work" | "expression" | "manifestation" | "item";
  summary?: RoadmapItemSummary;
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
    queryKey: queryKeys.roadmaps,
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
      qc.setQueryData(queryKeys.roadmaps, (old: RoadmapData[] | undefined) => {
        if (!old) return [data];
        if (old.some(r => r.id === data.id)) return old;
        return [data, ...old];
      });
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
    },
  });
}

/**
 * Custom hook to delete a reading roadmap.
 *
 * @returns Mutation result
 */
export function useDeleteRoadmap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (roadmapId: number) => {
      const res = await apiClient.delete(`/v1/roadmaps/${roadmapId}`);
      return res.data;
    },
    onSuccess: (_, roadmapId) => {
      qc.setQueryData(queryKeys.roadmaps, (old: RoadmapData[] | undefined) => {
        if (!old) return old;
        return old.filter(r => r.id !== roadmapId);
      });
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
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
      expressionId,
      itemId,
      notes,
    }: {
      roadmapId: number;
      manifestationId?: number;
      workId?: number;
      expressionId?: number;
      itemId?: number;
      notes?: string;
    }) => {
      const res = await apiClient.post<RoadmapItemData>(`/v1/roadmaps/${roadmapId}/items`, {
        manifestation_id: manifestationId,
        work_id: workId,
        expression_id: expressionId,
        item_id: itemId,
        notes,
      });
      return res.data;
    },
    onSuccess: (newItem, variables) => {
      qc.setQueryData(queryKeys.roadmaps, (old: RoadmapData[] | undefined) => {
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
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
    },
  });
}

/**
 * Custom hook to update target or notes of a roadmap item.
 *
 * @returns Mutation result
 */
export function useUpdateRoadmapItemTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      workId,
      expressionId,
      manifestationId,
      targetItemId,
      notes,
    }: {
      itemId: number;
      workId?: number;
      expressionId?: number;
      manifestationId?: number;
      targetItemId?: number;
      notes?: string;
    }) => {
      const res = await apiClient.patch<RoadmapItemData>(`/v1/roadmaps/items/${itemId}/target`, {
        work_id: workId,
        expression_id: expressionId,
        manifestation_id: manifestationId,
        item_id: targetItemId,
        notes,
      });
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
    },
  });
}

/**
 * Custom hook to delete a roadmap item.
 *
 * @returns Mutation result
 */
export function useDeleteRoadmapItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      const res = await apiClient.delete(`/v1/roadmaps/items/${itemId}`);
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
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
      void qc.invalidateQueries({ queryKey: queryKeys.roadmaps });
    },
  });
}
