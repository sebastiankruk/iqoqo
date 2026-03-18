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
import axios from "axios";
import type { ApiResponse } from "@/types/frbr";

// In the browser we always use a relative "/api" base so requests are same-origin
// and flow through the Next.js rewrite proxy (/api/:path* → Flask). This avoids
// CORS issues and ensures the httpOnly session cookie is forwarded to Flask.
// For server-side calls use lib/api/server-client.ts instead.
const API_BASE = "/api";

/**
 * Preconfigured axios instance pointing at the Flask backend.
 * withCredentials is intentionally omitted: no session-based auth is
 * implemented yet. Re-add it alongside CORS_SUPPORTS_CREDENTIALS=true
 * in .env when cookie/session auth is introduced.
 */
export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

/** Unwrap the standard `{ success, data, error }` envelope. */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error.response?.data?.error ??
      error.message ??
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

/**
 * Helper: GET and unwrap the `data` field from an ApiResponse envelope.
 *
 * @param path - The API path
 * @param params - Optional query parameters
 * @returns {Promise<T>} The unwrapped data
 */
export async function apiFetch<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const res = await apiClient.get<ApiResponse<T>>(path, { params });
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Unknown error");
  }
  return res.data.data;
}

/**
 * Fetch global instance statistics (works, manifestations, items, users)
 *
 * @returns {Promise<{ works: number; manifestations: number; items: number; users: number }>} The statistics
 */
export async function getGlobalStats(): Promise<{ works: number; manifestations: number; items: number; users: number }> {
  return apiFetch('/stats/global');
}

/**
 * Fetch most recent manifestations added to the instance
 *
 * @param limit - Maximum number of items to return
 * @returns {Promise<Record<string, unknown>[]>} The recent manifestations
 */
export async function getRecentManifestations(limit = 10) {
  return apiFetch<Record<string, unknown>[]>("/manifestations/recent", { limit });
}
