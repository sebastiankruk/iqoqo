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
import type { ApiResponse } from "@/types/frbr";
import type { FrbrTree } from "../admin";
import {
  updateFrbrEntity as updateFrbrEntityApi,
  type FrbrEntityUpdatePayload,
  type FrbrItem as FrbrItemType,
  getLodStats,
  getLodTaskStatus,
  getActiveLodTask,
  triggerLodReconciliation,
  cancelLodTask,
} from "../admin";
import type { LODReconciliationTriggerParams } from "@/types/admin";
import { ARRAY_META_FIELDS, ensureArray } from "@/components/admin/frbr/types";
import { getFrbrTree } from "../admin";
import { queryKeys } from "./query-keys";

/**
 * Normalizes array fields in metadata before API submission.
 * Ensures known array fields are always arrays, even if they slipped through as strings.
 *
 * @param meta - The metadata to normalize.
 * @returns The normalized metadata, or the original undefined value.
 */
function normalizeMetaForApi(meta: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!meta) return meta;
  const normalized = { ...meta };
  for (const key of ARRAY_META_FIELDS) {
    if (key in normalized) {
      normalized[key] = ensureArray(normalized[key]);
    }
  }
  return normalized;
}

/**
 * Normalizes array-valued metadata while retaining the entity-specific payload type.
 *
 * @param payload - The discriminated entity update payload.
 * @returns The payload with normalized metadata fields.
 */
function normalizeFrbrUpdate(payload: FrbrEntityUpdatePayload): FrbrEntityUpdatePayload {
  switch (payload.type) {
    case "work":
    case "expression":
    case "manifestation":
    case "item":
      return { ...payload, data: { ...payload.data, meta: normalizeMetaForApi(payload.data.meta) } };
  }
}

/**
 * Custom hook to fetch the full FRBR tree for a manifestation.
 *
 * @param manifestationId - The manifestation ID to load the tree for
 * @returns Query result containing the FrbrTree
 */
export function useFrbrTree(manifestationId: number) {
  return useQuery<FrbrTree>({
    queryKey: queryKeys.frbrTree(manifestationId),
    queryFn: () => getFrbrTree(manifestationId),
    enabled: manifestationId > 0,
    staleTime: 30_000,
  });
}

/**
 * Custom hook to update any FRBR entity with optimistic cache updates.
 *
 * On mutate: cancels outgoing queries, snapshots the current cache,
 * optimistically updates the tree, and returns a rollback context.
 * On error: reverts the cache to the previous snapshot.
 * On settled: invalidates the query to reconcile with server state.
 *
 * @returns Mutation result for updating FRBR entities
 */
export function useUpdateFrbrEntity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ manifestationId, ...payload }: { manifestationId: number } & FrbrEntityUpdatePayload) => {
      void manifestationId;
      return updateFrbrEntityApi(normalizeFrbrUpdate(payload));
    },
    onMutate: async ({ manifestationId, type, id, data }) => {
      const queryKey = queryKeys.frbrTree(manifestationId);
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<FrbrTree>(queryKey);

      qc.setQueryData<FrbrTree>(queryKey, old => {
        if (!old) return old;
        const updated = { ...old };
        if (type === "work" && updated.work && updated.work.id === id) {
          const { meta, ...rest } = data;
          updated.work = {
            ...updated.work,
            ...rest,
            meta: meta ? { ...updated.work.meta, ...(meta as Record<string, unknown>) } : updated.work.meta,
          } as typeof updated.work;
        } else if (type === "expression" && updated.expression && updated.expression.id === id) {
          const { meta, ...rest } = data;
          updated.expression = {
            ...updated.expression,
            ...rest,
            meta: meta ? { ...updated.expression.meta, ...(meta as Record<string, unknown>) } : updated.expression.meta,
          } as typeof updated.expression;
        } else if (type === "manifestation" && updated.manifestation.id === id) {
          const { meta, ...rest } = data;
          updated.manifestation = {
            ...updated.manifestation,
            ...rest,
            meta: meta
              ? { ...updated.manifestation.meta, ...(meta as Record<string, unknown>) }
              : updated.manifestation.meta,
          } as typeof updated.manifestation;
        } else if (type === "item") {
          updated.items = updated.items.map(item => {
            if (item.id === id) {
              const { meta, ...rest } = data;
              return {
                ...item,
                ...rest,
                meta: meta ? { ...item.meta, ...(meta as Record<string, unknown>) } : item.meta,
              } as FrbrItemType;
            }
            return item;
          });
        }
        return updated;
      });

      return { previous, queryKey };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(context.queryKey, context.previous);
      }
    },
    onSettled: (_data, _error, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.frbrTree(variables.manifestationId) });
    },
  });
}

/**
 * Custom hook to add a child entity to the FRBR hierarchy.
 *
 * Supports creating Expressions under Works, Manifestations under Expressions,
 * and Items under Manifestations.
 *
 * @returns Mutation result for adding child entities
 */
export function useAddFrbrChild() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      parentType,
      parentId,
      childType,
      data,
    }: {
      manifestationId: number;
      parentType: "work" | "expression" | "manifestation";
      parentId: number;
      childType: "expression" | "manifestation" | "item";
      data: Record<string, unknown>;
    }) => {
      const res = await apiClient.post<ApiResponse<{ id: number }>>(
        `/v1/admin/frbr/${parentType}/${parentId}/${childType}`,
        data
      );
      if (!res.data.success || !res.data.data) {
        throw new Error(res.data.error ?? `Failed to create ${childType}`);
      }
      return res.data.data;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.frbrTree(variables.manifestationId) });
    },
  });
}

/**
 * Custom hook to delete a FRBR entity with cache eviction.
 *
 * @returns Mutation result for deleting FRBR entities
 */
export function useDeleteFrbrEntity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      type,
      id,
    }: {
      manifestationId: number;
      type: "work" | "expression" | "manifestation" | "item";
      id: number;
    }) => {
      await apiClient.delete(`/v1/admin/frbr/${type}/${id}`);
      return { type, id };
    },
    onMutate: async ({ manifestationId, type, id }) => {
      const queryKey = queryKeys.frbrTree(manifestationId);
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<FrbrTree>(queryKey);

      qc.setQueryData<FrbrTree>(queryKey, old => {
        if (!old) return old;
        const updated = { ...old };
        if (type === "work" && updated.work?.id === id) {
          updated.work = null;
        } else if (type === "expression" && updated.expression?.id === id) {
          updated.expression = null;
        } else if (type === "item") {
          updated.items = updated.items.filter(item => item.id !== id);
        }
        return updated;
      });

      return { previous, queryKey };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(context.queryKey, context.previous);
      }
    },
    onSettled: (_data, _error, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.frbrTree(variables.manifestationId) });
    },
  });
}

// ---------------------------------------------------------------------------
// Linked Open Data (LOD) Hooks
// ---------------------------------------------------------------------------

/**
 * Custom hook to fetch lifetime Linked Open Data catalog statistics.
 *
 * @returns Query result containing the LODStats
 */
export function useLodStats() {
  return useQuery({
    queryKey: queryKeys.lodStats,
    queryFn: () => getLodStats(),
    staleTime: 10_000,
  });
}

/**
 * Custom hook to poll the status and progress of an active LOD reconciliation task.
 *
 * Polls every 1500ms while the task is pending or processing, and stops
 * automatically upon completion or failure.
 *
 * @param taskId - The Celery task ID, or null if no task is active
 * @returns Query result containing the LODReconciliationTaskStatus
 */
export function useLodTaskStatus(taskId: string | null) {
  return useQuery({
    queryKey: queryKeys.lodTaskStatus(taskId),
    queryFn: () => {
      if (!taskId) throw new Error("Task ID is required");
      return getLodTaskStatus(taskId);
    },
    enabled: Boolean(taskId),
    refetchInterval: query => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 1500;
    },
    refetchIntervalInBackground: true,
  });
}

/**
 * Custom hook to trigger batch Linked Open Data reconciliation across the catalog.
 *
 * Invalidates LOD statistics and the specific task query upon success.
 *
 * @returns Mutation result for triggering LOD reconciliation
 */
export function useTriggerLodReconciliation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params?: LODReconciliationTriggerParams) => triggerLodReconciliation(params),
    onSuccess: data => {
      qc.invalidateQueries({ queryKey: queryKeys.lodStats });
      if (data?.task_id) {
        qc.invalidateQueries({ queryKey: queryKeys.lodTaskStatus(data.task_id) });
        qc.invalidateQueries({ queryKey: queryKeys.lodActiveTask });
      }
    },
  });
}

/**
 * Custom hook to retrieve the currently active LOD reconciliation task, if any.
 *
 * Useful for restoring state across page navigations and reloads.
 *
 * @returns Query result containing the active task ID and state
 */
export function useActiveLodTask() {
  return useQuery({
    queryKey: queryKeys.lodActiveTask,
    queryFn: () => getActiveLodTask(),
    staleTime: 0,
    refetchOnMount: "always",
  });
}

/**
 * Custom hook to cancel an active LOD reconciliation task.
 *
 * Invalidates LOD active task, task status, and stats upon success.
 *
 * @returns Mutation result for cancelling LOD reconciliation
 */
export function useCancelLodTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId?: string | null) => cancelLodTask(taskId),
    onSuccess: data => {
      qc.invalidateQueries({ queryKey: queryKeys.lodActiveTask });
      qc.invalidateQueries({ queryKey: queryKeys.lodStats });
      if (data?.task_id) {
        qc.invalidateQueries({ queryKey: queryKeys.lodTaskStatus(data.task_id) });
      }
    },
  });
}
