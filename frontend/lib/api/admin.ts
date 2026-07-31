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
import { apiFetch, apiClient } from "./client";
import type { ApiResponse } from "@/types/frbr";

export interface AdminUser {
  id: string;
  email: string;
  display_name?: string | null;
  roles: string[];
  is_active: boolean;
}

/**
 * Fetch a paginated and filtered list of users.
 *
 * @param params - Query parameters
 * @param params.search - Search term for email or display name
 * @param params.status - Filter by status (active/inactive)
 * @param params.page - Page number
 * @param params.limit - Items per page
 * @returns The users and pagination metadata
 */
export async function getUsers(params?: {
  search?: string;
  status?: string;
  page?: number;
  limit?: number;
}): Promise<{ data: AdminUser[]; meta: { total: number; page: number; pages: number } }> {
  const query = new URLSearchParams();
  if (params?.search) query.append("search", params.search);
  if (params?.status && params.status !== "all") query.append("status", params.status);
  if (params?.page) query.append("page", params.page.toString());
  if (params?.limit) query.append("limit", params.limit.toString());

  const res = await apiClient.get<ApiResponse<AdminUser[]>>(`/v1/admin/users?${query.toString()}`);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch users");
  }

  // Bypass strict ApiResponse limits to capture pagination metadata
  const meta = (res.data as unknown as { meta: { total: number; page: number; pages: number } }).meta;
  return { data: res.data.data as AdminUser[], meta };
}

/**
 * Update user roles and status.
 *
 * @param userId - The user ID
 * @param data - The update data
 * @returns The updated user
 */
export async function updateUser(userId: string, data: Partial<AdminUser>): Promise<AdminUser> {
  const res = await apiClient.put<ApiResponse<AdminUser>>(`/v1/admin/users/${userId}`, data);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update user");
  }
  return res.data.data as AdminUser;
}

/**
 * Role data from API.
 */
export interface Role {
  id: number;
  name: string;
  is_protected?: boolean;
  member_count?: number;
  permission_count?: number;
}

/**
 * Fetch all available roles for RBAC assignment.
 *
 * @returns The roles
 */
export async function getRoles(): Promise<Role[]> {
  const res = await apiClient.get<ApiResponse<Role[]>>("/v1/admin/roles");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch roles");
  }
  return res.data.data;
}

/**
 * Create a new role.
 *
 * @param name - The role name
 * @returns The created role
 */
export async function createRole(name: string): Promise<Role> {
  const res = await apiClient.post<ApiResponse<Role>>("/v1/admin/roles", { name });
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to create role");
  }
  return res.data.data;
}

/**
 * Delete a role by ID.
 *
 * @param roleId - The role ID to delete
 */
export async function deleteRole(roleId: number): Promise<void> {
  const res = await apiClient.delete<ApiResponse<null>>(`/v1/admin/roles/${roleId}`);
  if (!res.data.success) {
    throw new Error(res.data.error ?? "Failed to delete role");
  }
}

/**
 * Permission data from API.
 */
export interface Permission {
  id: number;
  name: string;
  description?: string;
}

/**
 * Fetch all available permissions that can be assigned to roles.
 *
 * @returns The permissions
 */
export async function getPermissions(): Promise<Permission[]> {
  const res = await apiClient.get<ApiResponse<Permission[]>>("/v1/admin/permissions");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch permissions");
  }
  return res.data.data;
}

/**
 * Role permissions data from API.
 */
export interface RolePermissions {
  role_id: number;
  role_name: string;
  permission_ids: number[];
}

/**
 * Fetch permissions for a specific role.
 *
 * @param roleId - The role ID
 * @returns The role permissions
 */
export async function getRolePermissions(roleId: number): Promise<RolePermissions> {
  const res = await apiClient.get<ApiResponse<RolePermissions>>(`/v1/admin/roles/${roleId}/permissions`);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch role permissions");
  }
  return res.data.data;
}

/**
 * Update permissions for a specific role.
 *
 * @param roleId - The role ID
 * @param permissionIds - Array of permission IDs to assign
 * @returns The updated role permissions
 */
export async function updateRolePermissions(roleId: number, permissionIds: number[]): Promise<RolePermissions> {
  const res = await apiClient.put<ApiResponse<RolePermissions>>(`/v1/admin/roles/${roleId}/permissions`, {
    permission_ids: permissionIds,
  });
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update role permissions");
  }
  return res.data.data;
}

/**
 * Fetch instance settings.
 *
 * @param category - Optional category filter (external_apis, federation, affiliate, internal)
 * @returns The settings
 */
export async function getInstanceSettings(category?: string): Promise<Record<string, unknown>> {
  const query = category ? `?category=${category}` : "";
  return apiFetch<Record<string, unknown>>(`/v1/admin/settings${query}`);
}

/**
 * Update instance settings.
 *
 * @param settings - The new settings
 * @param category - Optional category for RBAC verification
 * @returns The updated settings
 */
export async function updateInstanceSettings(
  settings: Record<string, unknown>,
  category?: string
): Promise<Record<string, unknown>> {
  const query = category ? `?category=${category}` : "";
  const res = await apiClient.put<ApiResponse<Record<string, unknown>>>(`/v1/admin/settings${query}`, settings);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update settings");
  }
  return res.data.data;
}

/**
 * Reveal a masked setting value.
 *
 * @param key - The setting key to reveal
 * @returns The unmasked value
 */
export async function revealSettingValue(key: string): Promise<{ value: string }> {
  const res = await apiClient.get<ApiResponse<{ value: string }>>(`/v1/admin/settings/reveal?key=${key}`);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to reveal setting");
  }
  return res.data.data;
}

// --- FRBR ENTITY TYPES ---

export interface FrbrWork {
  id: number;
  title: string;
  meta: Record<string, unknown>;
}

export interface FrbrExpression {
  id: number;
  work_id: number;
  content_type: string;
  language: string;
  kind?: string | null;
  meta: Record<string, unknown>;
}

export interface FrbrManifestation {
  id: number;
  expression_id: number;
  isbn13: string | null;
  upc: string | null;
  ean: string | null;
  publisher: string | null;
  publication_date: string | null;
  meta: Record<string, unknown>;
}

export interface FrbrItem {
  id: number;
  status: string;
  condition: string | null;
  meta: Record<string, unknown>;
  owner_id: string;
  owner_name?: string;
}

export interface FrbrTree {
  work: FrbrWork | null;
  expression: FrbrExpression | null;
  manifestation: FrbrManifestation;
  items: FrbrItem[];
}

export interface FrbrSearchResult {
  id: number;
  title: string;
  type: "work" | "expression" | "manifestation";
  isbn13?: string | null;
  upc?: string | null;
  ean?: string | null;
  content_type?: string;
}

/**
 * Fetch the full FRBR lineage for a manifestation.
 *
 * @param manifestationId - The manifestation ID
 * @returns The FRBR tree (Work -> Expression -> Manifestation -> Items)
 */
export async function getFrbrTree(manifestationId: number): Promise<FrbrTree> {
  return apiFetch<FrbrTree>(`/v1/admin/frbr/tree/manifestation/${manifestationId}`);
}

/**
 * Update a Work entity.
 *
 * @param workId - The work ID
 * @param data - The update data
 * @param data.title - Optional new title
 * @param data.meta - Optional new metadata
 * @returns The updated work ID
 */
export async function updateFrbrWork(
  workId: number,
  data: { title?: string; meta?: Record<string, unknown> }
): Promise<{ id: number }> {
  const res = await apiClient.put<ApiResponse<{ id: number }>>(`/v1/admin/frbr/work/${workId}`, data);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update work");
  }
  return res.data.data;
}

/**
 * Update an Expression entity.
 *
 * @param expressionId - The expression ID
 * @param data - The update data
 * @param data.work_id - Optional new work ID association
 * @param data.content_type - Optional new content type
 * @param data.language - Optional new language
 * @param data.kind - Optional new expression kind (e.g. "live_performance"; empty string clears to studio/default)
 * @param data.meta - Optional new metadata
 * @returns The updated expression ID
 */
export async function updateFrbrExpression(
  expressionId: number,
  data: { work_id?: number; content_type?: string; language?: string; kind?: string; meta?: Record<string, unknown> }
): Promise<{ id: number }> {
  const res = await apiClient.put<ApiResponse<{ id: number }>>(`/v1/admin/frbr/expression/${expressionId}`, data);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update expression");
  }
  return res.data.data;
}

/**
 * Update a Manifestation entity.
 *
 * @param manifestationId - The manifestation ID
 * @param data - The update data
 * @param data.expression_id - Optional new expression ID association
 * @param data.isbn13 - Optional new ISBN-13
 * @param data.upc - Optional new UPC
 * @param data.ean - Optional new EAN
 * @param data.publisher - Optional new publisher name
 * @param data.publication_date - Optional new publication date string
 * @param data.meta - Optional new metadata
 * @returns The updated manifestation ID
 */
export async function updateFrbrManifestation(
  manifestationId: number,
  data: {
    expression_id?: number;
    isbn13?: string;
    upc?: string;
    ean?: string;
    publisher?: string;
    publication_date?: string;
    meta?: Record<string, unknown>;
  }
): Promise<{ id: number }> {
  const res = await apiClient.put<ApiResponse<{ id: number }>>(`/v1/admin/frbr/manifestation/${manifestationId}`, data);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update manifestation");
  }
  return res.data.data;
}

/**
 * Update an Item entity.
 *
 * @param itemId - The item ID
 * @param data - The update data
 * @param data.manifestation_id - Optional new manifestation ID association
 * @param data.status - Optional new status
 * @param data.condition - Optional new condition
 * @param data.meta - Optional new metadata
 * @returns The updated item ID
 */
export async function updateFrbrItem(
  itemId: number,
  data: { manifestation_id?: number; status?: string; condition?: string; meta?: Record<string, unknown> }
): Promise<{ id: number }> {
  const res = await apiClient.put<ApiResponse<{ id: number }>>(`/v1/admin/frbr/item/${itemId}`, data);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update item");
  }
  return res.data.data;
}

/**
 * Unified function to update any FRBR entity.
 *
 * @param type - Entity type (work, expression, manifestation, item)
 * @param id - Entity ID
 * @param data - Update data
 * @returns The updated entity ID
 */
export async function updateFrbrEntity(
  type: "work" | "expression" | "manifestation" | "item",
  id: number,
  data: Record<string, unknown>
): Promise<{ id: number }> {
  switch (type) {
    case "work":
      return updateFrbrWork(id, data as { title?: string; meta?: Record<string, unknown> });
    case "expression":
      return updateFrbrExpression(
        id,
        data as {
          work_id?: number;
          content_type?: string;
          language?: string;
          kind?: string;
          meta?: Record<string, unknown>;
        }
      );
    case "manifestation":
      return updateFrbrManifestation(id, data as Parameters<typeof updateFrbrManifestation>[1]);
    case "item":
      return updateFrbrItem(
        id,
        data as { manifestation_id?: number; status?: string; condition?: string; meta?: Record<string, unknown> }
      );
  }
}

/**
 * Search for FRBR entities by title or identifier.
 *
 * @param query - Search query
 * @param entityType - Entity type to search (work, expression, manifestation)
 * @param limit - Max results
 * @returns Search results
 */
export async function searchFrbrEntities(
  query: string,
  entityType: "work" | "expression" | "manifestation" = "manifestation",
  limit: number = 20
): Promise<FrbrSearchResult[]> {
  const params = new URLSearchParams({ q: query, type: entityType, limit: limit.toString() });
  const res = await apiFetch<FrbrSearchResult[]>(`/v1/admin/frbr/search?${params.toString()}`);
  return res;
}

export interface UploadCoverResponse {
  success: boolean;
  data?: {
    cover_url: string;
  };
  error?: string;
}

/**
 * Upload a cropped cover art blob to be attached to a specific entity.
 *
 * @param entityType - Either 'manifestation' or 'item'.
 * @param entityId - The target entity ID.
 * @param blob - The generated valid blob payload.
 * @param filename - Optional target filename (defaults to cover.jpg).
 * @returns The api response metadata.
 */
export async function uploadEntityCover(
  entityType: "manifestation" | "item",
  entityId: number,
  blob: Blob,
  filename: string = "cover.jpg"
): Promise<UploadCoverResponse> {
  const formData = new FormData();
  formData.append("file", blob, filename);
  formData.append("entity_type", entityType);
  formData.append("entity_id", entityId.toString());

  const response = await apiClient.post<UploadCoverResponse>("/v1/admin/media/upload-cover", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}
