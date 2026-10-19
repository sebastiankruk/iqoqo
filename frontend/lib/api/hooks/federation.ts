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
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getFederationInstances,
  addFederationInstance,
  updateInstanceTrust,
  removeFederationInstance,
  getFederationActivities,
  getFederationKeyFingerprint,
} from "@/lib/api/federation";
import { queryKeys } from "./query-keys";
import type { FederationActivityFilters, TrustLevel } from "@/types/federation";

/**
 * Hook to retrieve all registered federation peer instances.
 */
export function useFederationInstances() {
  return useQuery({
    queryKey: queryKeys.federationInstances,
    queryFn: () => getFederationInstances(),
    staleTime: 30000,
  });
}

/**
 * Hook to manually add and discover a federation peer instance by domain.
 */
export function useAddFederationInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (domain: string) => addFederationInstance(domain),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.federationInstances });
    },
  });
}

/**
 * Hook to update trust level for a federation instance.
 */
export function useUpdateInstanceTrust() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ instanceId, trustLevel }: { instanceId: number; trustLevel: TrustLevel }) =>
      updateInstanceTrust(instanceId, trustLevel),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.federationInstances });
    },
  });
}

/**
 * Hook to remove a federation instance from the registry.
 */
export function useRemoveFederationInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (instanceId: number) => removeFederationInstance(instanceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.federationInstances });
    },
  });
}

/**
 * Hook to fetch paginated federation activities with optional filters.
 */
export function useFederationActivities(page: number = 1, filters?: FederationActivityFilters) {
  return useQuery({
    queryKey: queryKeys.federationActivities(page, filters as Record<string, string | undefined>),
    queryFn: () => getFederationActivities(page, filters),
    staleTime: 10000,
  });
}

/**
 * Hook to fetch the instance actor public key SHA-256 fingerprint.
 */
export function useFederationKeyFingerprint() {
  return useQuery({
    queryKey: queryKeys.federationKeyFingerprint,
    queryFn: () => getFederationKeyFingerprint(),
    staleTime: 60000,
  });
}
