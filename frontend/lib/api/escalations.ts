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

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, apiFetch } from "./client";
import type { EscalationRequest } from "@/types/frbr";

export const escalationQueryKeys = {
  mine: ["escalations", "mine"] as const,
  queue: ["escalations", "queue"] as const,
  resolved: ["escalations", "queue", "resolved"] as const,
};

/**
 * Submit a metadata escalation request for a specific FRBR entity.
 *
 * @param level - The FRBR level ('work', 'expression', 'manifestation', 'item').
 * @param targetId - The target entity ID.
 * @param data - The escalation payload containing field_name and suggested_value.
 * @param data.field_name - Name of the field to correct.
 * @param data.suggested_value - Suggested correct value.
 * @param data.current_value - Current incorrect value (optional).
 * @param data.note - Additional context or justification note (optional).
 * @returns The created EscalationRequest.
 */
export async function createEscalation(
  level: string,
  targetId: number,
  data: {
    field_name: string;
    suggested_value: string;
    current_value?: string;
    note?: string;
    request_type?: "correction" | "deletion";
  }
) {
  const res = await apiClient.post<{ success: boolean; data: EscalationRequest }>(
    `/escalations/${level}/${targetId}`,
    data
  );
  return res.data.data;
}

/**
 * Fetch escalation requests submitted by the current user.
 *
 * @returns Array of user's escalation requests.
 */
export async function getMyEscalations(): Promise<EscalationRequest[]> {
  return apiFetch<EscalationRequest[]>("/escalations/mine");
}

/**
 * Fetch escalation requests for custodian review queue.
 *
 * @param status - Comma-separated statuses to filter by. Defaults to "pending".
 * @returns Array of escalation requests.
 */
export async function getEscalationQueue(status = "pending"): Promise<EscalationRequest[]> {
  const params = new URLSearchParams({ status });
  return apiFetch<EscalationRequest[]>(`/escalations/queue?${params.toString()}`);
}

/**
 * Resolve a pending escalation request.
 *
 * @param escalationId - The ID of the escalation request.
 * @param data - The resolution status and optional resolution note.
 * @param data.status - Status transition ('accepted', 'rejected', 'duplicate').
 * @param data.resolution_note - Custodian note explaining resolution (optional).
 * @returns The updated EscalationRequest.
 */
export async function resolveEscalation(
  escalationId: number,
  data: {
    status: "accepted" | "rejected" | "duplicate";
    resolution_note?: string;
  }
) {
  const res = await apiClient.patch<{ success: boolean; data: EscalationRequest }>(
    `/escalations/${escalationId}`,
    data
  );
  return res.data.data;
}

/**
 * Hook to fetch escalation requests submitted by the current user.
 *
 * @param enabled - Whether the query should be executed.
 * @returns Query result containing the user's escalation requests.
 */
export function useMyEscalations(enabled = true) {
  return useQuery<EscalationRequest[]>({
    queryKey: escalationQueryKeys.mine,
    queryFn: () => getMyEscalations(),
    enabled,
    staleTime: 10_000,
  });
}

/**
 * Hook to fetch escalation requests in the custodian queue.
 *
 * @param status - Comma-separated statuses to filter by. Defaults to "pending".
 * @param enabled - Whether the query should be executed.
 * @returns Query result containing the custodian queue.
 */
export function useEscalationQueue(status = "pending", enabled = true) {
  return useQuery<EscalationRequest[]>({
    queryKey: [...escalationQueryKeys.queue, status],
    queryFn: () => getEscalationQueue(status),
    enabled,
    staleTime: 10_000,
  });
}

/**
 * Hook to fetch resolved (non-pending) escalation requests for processed history.
 *
 * @param enabled - Whether the query should be executed.
 * @returns Query result containing resolved escalation requests.
 */
export function useResolvedEscalations(enabled = true) {
  return useEscalationQueue("accepted,rejected,duplicate", enabled);
}

/**
 * Hook to create a new escalation request.
 *
 * @returns Mutation result for creating an escalation.
 */
export function useCreateEscalation() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      level,
      targetId,
      data,
    }: {
      level: string;
      targetId: number;
      data: {
        field_name: string;
        suggested_value: string;
        current_value?: string;
        note?: string;
        request_type?: "correction" | "deletion";
      };
    }) => createEscalation(level, targetId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: escalationQueryKeys.mine });
    },
  });
}

/**
 * Hook to resolve a pending escalation request.
 *
 * @returns Mutation result for resolving an escalation.
 */
export function useResolveEscalation() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      escalationId,
      data,
    }: {
      escalationId: number;
      data: {
        status: "accepted" | "rejected" | "duplicate";
        resolution_note?: string;
      };
    }) => resolveEscalation(escalationId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: escalationQueryKeys.queue });
      qc.invalidateQueries({ queryKey: escalationQueryKeys.mine });
    },
  });
}
