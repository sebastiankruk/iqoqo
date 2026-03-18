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

/**
 * Fetch a list of users.
 *
 * @returns {Promise<Record<string, unknown>[]>} The users
 */
export async function getUsers(): Promise<Record<string, unknown>[]> {
  return apiFetch<Record<string, unknown>[]>('/v1/admin/users');
}

/**
 * Fetch instance settings.
 *
 * @returns {Promise<Record<string, unknown>>} The settings
 */
export async function getInstanceSettings(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/v1/admin/settings");
}

/**
 * Update instance settings.
 *
 * @param settings - The new settings
 * @returns {Promise<Record<string, unknown>>} The updated settings
 */
export async function updateInstanceSettings(settings: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await apiClient.put<ApiResponse<Record<string, unknown>>>("/v1/admin/settings", settings);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update settings");
  }
  return res.data.data;
}
