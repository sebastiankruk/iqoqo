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
import { apiClient } from "./client";
import type { ApiResponse } from "@/types/frbr";
import type {
  FederationActivity,
  FederationActivityFilters,
  FederationConsent,
  FederationDirectoryData,
  FederationInstance,
  PaginationMeta,
  TrustLevel,
} from "@/types/federation";

// ---------------------------------------------------------------------------
// Federation Instances
// ---------------------------------------------------------------------------

/**
 * Fetch all federation instances.
 * @returns Promise resolving to the list of federation instances
 */
export async function getFederationInstances(): Promise<FederationInstance[]> {
  const res = await apiClient.get<ApiResponse<FederationInstance[]>>("/v1/admin/federation/instances");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch federation instances");
  }
  return res.data.data;
}

/**
 * Add a new federation instance by domain.
 * @param domain - The domain of the remote instance
 * @returns Promise resolving to the created federation instance
 */
export async function addFederationInstance(domain: string): Promise<FederationInstance> {
  const res = await apiClient.post<ApiResponse<FederationInstance>>("/v1/admin/federation/instances", { domain });
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to add federation instance");
  }
  return res.data.data;
}

/**
 * Update trust level for an instance.
 * @param instanceId - The database ID of the instance
 * @param trustLevel - The new trust level to set
 * @returns Promise resolving to the updated federation instance
 */
export async function updateInstanceTrust(instanceId: number, trustLevel: TrustLevel): Promise<FederationInstance> {
  const res = await apiClient.put<ApiResponse<FederationInstance>>(
    `/v1/admin/federation/instances/${instanceId}/trust`,
    { trust_level: trustLevel }
  );
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update trust level");
  }
  return res.data.data;
}

/**
 * Remove a federation instance.
 * @param instanceId - The database ID of the instance to remove
 */
export async function removeFederationInstance(instanceId: number): Promise<void> {
  const res = await apiClient.delete<ApiResponse<{ deleted: boolean }>>(`/v1/admin/federation/instances/${instanceId}`);
  if (!res.data.success) {
    throw new Error(res.data.error ?? "Failed to remove instance");
  }
}

/** Aliases for federation instance administration */
export const listFederationInstances = getFederationInstances;
export const updateFederationInstance = updateInstanceTrust;
export const deleteFederationInstance = removeFederationInstance;

/**
 * Fetch instance actor public key fingerprint.
 * @returns Promise resolving to the key fingerprint
 */
export async function getFederationKeyFingerprint(): Promise<string> {
  const res = await apiClient.get<ApiResponse<{ fingerprint: string }>>("/v1/admin/federation/key-fingerprint");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch key fingerprint");
  }
  return res.data.data.fingerprint;
}

/**
 * Provision or rotate instance actor keypair.
 * @param rotate - Whether to rotate an existing key
 * @returns Promise resolving to the resulting key fingerprint
 */
export async function provisionFederationInstanceKey(rotate: boolean = false): Promise<string> {
  const res = await apiClient.post<ApiResponse<{ fingerprint: string }>>(
    "/v1/admin/federation/key-fingerprint/provision",
    { rotate }
  );
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to provision instance key");
  }
  return res.data.data.fingerprint;
}

// ---------------------------------------------------------------------------
// Federation Activities
// ---------------------------------------------------------------------------

/**
 * Fetch paginated federation activities with optional filters.
 * @param page - Page number (default 1)
 * @param filters - Optional activity filters
 * @returns Promise resolving to activities and pagination metadata
 */
export async function getFederationActivities(
  page: number = 1,
  filters?: FederationActivityFilters
): Promise<{ data: FederationActivity[]; pagination: PaginationMeta }> {
  const params = new URLSearchParams({ page: page.toString() });
  if (filters?.direction) params.append("direction", filters.direction);
  if (filters?.type) params.append("type", filters.type);
  if (filters?.status) params.append("status", filters.status);

  const res = await apiClient.get<{
    success: boolean;
    data: FederationActivity[];
    pagination: PaginationMeta;
    error?: string;
  }>(`/v1/admin/federation/activities?${params.toString()}`);

  if (!res.data.success) {
    throw new Error(res.data.error ?? "Failed to fetch activities");
  }
  return { data: res.data.data, pagination: res.data.pagination };
}

/** Alias for federation activities listing */
export const listFederationActivities = getFederationActivities;

// ---------------------------------------------------------------------------
// Federation Consent (User-facing)
// ---------------------------------------------------------------------------

/**
 * Fetch current user's federation consent settings.
 * @returns Promise resolving to the consent object or null
 */
export async function getFederationConsent(): Promise<FederationConsent | null> {
  try {
    const res = await apiClient.get<ApiResponse<FederationConsent>>("/v1/profile/federation-consent");
    if (!res.data.success) return null;
    return res.data.data;
  } catch {
    return null;
  }
}

/**
 * Update current user's federation consent settings.
 * @param consent - Partial consent fields to update
 * @returns Promise resolving to the updated consent object
 */
export async function updateFederationConsent(consent: Partial<FederationConsent>): Promise<FederationConsent> {
  const res = await apiClient.put<ApiResponse<FederationConsent>>("/v1/profile/federation-consent", consent);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update consent");
  }
  return res.data.data;
}

// ---------------------------------------------------------------------------
// Cross-Instance Discovery & Interaction
// ---------------------------------------------------------------------------

export interface RemoteActorLookupResult {
  success: boolean;
  handle: string;
  actor_uri: string;
  actor: Record<string, unknown>;
}

export interface RemoteFollowResult {
  success: boolean;
  status: string;
  activity: Record<string, unknown>;
  remote_actor: Record<string, unknown>;
}

/**
 * Resolve remote actor handle via WebFinger and retrieve Actor JSON-LD document.
 * @param handle - Remote actor handle (e.g. @alice@remote.iqoqo.test)
 */
export async function lookupRemoteActor(handle: string): Promise<RemoteActorLookupResult> {
  const params = new URLSearchParams({ handle });
  const res = await apiClient.get<ApiResponse<RemoteActorLookupResult>>(`/federation/lookup?${params.toString()}`);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to lookup remote actor");
  }
  return res.data.data;
}

/**
 * Send an ActivityPub Follow activity to a remote Actor's inbox.
 * @param params - Either handle or actor_uri and optional inbox_url
 * @param params.handle - Remote actor handle
 * @param params.actor_uri - Remote actor URI
 * @param params.inbox_url - Optional inbox URL
 */
export async function followRemoteActor(params: {
  handle?: string;
  actor_uri?: string;
  inbox_url?: string;
}): Promise<RemoteFollowResult> {
  const res = await apiClient.post<ApiResponse<RemoteFollowResult>>("/federation/follow", params);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to follow remote actor");
  }
  return res.data.data;
}

/**
 * Fetch connected federated library directory and instance stats.
 * @returns Promise resolving to directory overview
 */
export async function getFederationDirectory(): Promise<FederationDirectoryData> {
  const res = await apiClient.get<ApiResponse<FederationDirectoryData>>("/federation/directory");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch federation directory");
  }
  return res.data.data;
}
