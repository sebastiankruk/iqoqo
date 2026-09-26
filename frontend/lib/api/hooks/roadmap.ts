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
        return [data, ...old];
      });
      void qc.invalidateQueries({ queryKey: ["roadmaps"] });
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
      qc.setQueryData(["roadmaps"], (old: RoadmapData[] | undefined) => {
        if (!old) return old;
        return old.filter(r => r.id !== roadmapId);
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
