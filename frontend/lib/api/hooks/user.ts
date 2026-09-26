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

import { useQuery } from "@tanstack/react-query";
import { apiClient, apiFetch } from "../client";
import type { ApiResponse, UserProfile } from "@/types/frbr";
import axios from "axios";

/**
 * Custom hook to fetch the user profile.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<UserProfile | null>} Query result
 */
export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      try {
        return await apiFetch<UserProfile>("/profile/");
      } catch (err) {
        if (axios.isAxiosError(err) && (err.response?.status === 401 || err.response?.status === 404)) {
          await fetch("/api/auth/logout", { method: "POST" });
        }
        return null;
      }
    },
    retry: false,
    staleTime: 0,
  });
}

/**
 * Custom hook to search users by name or email.
 *
 * @param query - The search query
 * @param enabled - Whether the query is enabled
 * @returns {import('@tanstack/react-query').UseQueryResult<UserProfile[]>} Query result
 */
export function useUserSearch(query: string, enabled = false) {
  return useQuery({
    queryKey: ["users", "search", query],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UserProfile[]>>("/profile/users/search", { params: { q: query } });
      return res.data?.data ?? [];
    },
    enabled: enabled && query.trim().length >= 2,
    staleTime: 60_000,
  });
}
