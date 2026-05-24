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
 * Get the current user's intent for a given Conceptual Work (F1).
 *
 * @param workId - The database ID of the Work
 * @returns Promise resolving to the intent status string or null
 */
export async function getWorkIntent(workId: number): Promise<string | null> {
  const res = await apiFetch<{ status: string | null }>(`/works/${workId}/intent`);
  return res.status;
}

/**
 * Set or update the current user's intent for a given Conceptual Work (F1).
 *
 * @param workId - The database ID of the Work
 * @param status - The progress status (e.g. 'want_to_read') or null to clear
 * @returns Promise resolving to the set intent status or null
 */
export async function setWorkIntent(workId: number, status: string | null): Promise<string | null> {
  const res = await apiClient.post<ApiResponse<{ status: string | null }>>(`/works/${workId}/intent`, {
    status,
  });
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Failed to set work intent");
  }
  return res.data.data.status;
}

/**
 * Delete the current user's intent for a given Conceptual Work (F1).
 *
 * @param workId - The database ID of the Work
 * @returns Promise resolving to null
 */
export async function deleteWorkIntent(workId: number): Promise<null> {
  const res = await apiClient.delete<ApiResponse<{ status: null }>>(`/works/${workId}/intent`);
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Failed to delete work intent");
  }
  return null;
}
