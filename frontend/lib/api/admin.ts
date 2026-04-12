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
 * Fetch all available roles for RBAC assignment.
 *
 * @returns The roles
 */
export async function getRoles(): Promise<{ id: number; name: string }[]> {
  const res = await apiClient.get<ApiResponse<{ id: number; name: string }[]>>("/v1/admin/roles");
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to fetch roles");
  }
  return res.data.data;
}

/**
 * Fetch instance settings.
 *
 * @returns The settings
 */
export async function getInstanceSettings(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/v1/admin/settings");
}

/**
 * Update instance settings.
 *
 * @param settings - The new settings
 * @returns The updated settings
 */
export async function updateInstanceSettings(settings: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await apiClient.put<ApiResponse<Record<string, unknown>>>("/v1/admin/settings", settings);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update settings");
  }
  return res.data.data;
}
