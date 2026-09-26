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
import { getVelocityInsights, getDistributionInsights } from "../profile";
import type { VelocityPoint, InsightsData } from "@/types/insights";
import type { DashboardStats, ApiResponse, FacetStatsResponse } from "@/types/frbr";
import { queryKeys } from "./query-keys";

/* ── Dashboard stats ─────────────────────────────────────────────────────── */

/**
 * Custom hook to fetch dashboard statistics.
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns {import('@tanstack/react-query').UseQueryResult<DashboardStats>} Query result
 */
export function useStats(scope: "personal" | "global" = "personal") {
  return useQuery({
    queryKey: queryKeys.stats(scope),
    queryFn: () => apiFetch<DashboardStats>(`/stats?scope=${scope}`),
    staleTime: 30_000,
  });
}

/**
 * Custom hook to fetch global statistics.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<{ works: number; manifestations: number; items: number; users: number }>} Query result
 */
export function useGlobalStats() {
  return useQuery({
    queryKey: ["globalStats"],
    queryFn: () => apiFetch<{ works: number; manifestations: number; items: number; users: number }>("/stats/global"),
    staleTime: 60_000,
  });
}

/**
 * Custom hook to fetch cross-filtered facet counts for the sidebar.
 *
 * @param scope - The scope to fetch stats for ("global" or "user")
 * @param filters - Filter params to narrow counts
 * @param enabled - Whether the query is enabled
 * @returns React Query result with per-facet counts
 */
export function useFacetStats(scope: "global" | "user", filters?: Record<string, string>, enabled = true) {
  return useQuery({
    queryKey: ["facetStats", scope, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("scope", scope);
      if (filters) {
        Object.entries(filters).forEach(([k, v]) => {
          if (v) params.set(k, v);
        });
      }
      const res = await apiClient.get<ApiResponse<FacetStatsResponse>>(`/stats/facets?${params.toString()}`);
      return res.data.data ?? ({} as FacetStatsResponse);
    },
    staleTime: 30_000,
    enabled,
  });
}

/**
 * Custom hook to fetch acquisition velocity insights.
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns Query result
 */
export function useVelocityInsights(scope: "personal" | "global" = "personal") {
  return useQuery<VelocityPoint[]>({
    queryKey: ["insights", "velocity", scope],
    queryFn: () => getVelocityInsights(scope),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Custom hook to fetch distribution insights (content types & formats).
 *
 * @param scope - Data scope ('personal' | 'global')
 * @returns Query result
 */
export function useDistributionInsights(scope: "personal" | "global" = "personal") {
  return useQuery<InsightsData>({
    queryKey: ["insights", "distribution", scope],
    queryFn: () => getDistributionInsights(scope),
    staleTime: 5 * 60 * 1000,
  });
}
