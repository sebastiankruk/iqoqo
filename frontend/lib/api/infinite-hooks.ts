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

"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { ApiResponse } from "@/types/frbr";

interface FetchItemsParams {
  viewMode: "manifestations" | "works" | "items";
  filters: Record<string, string | string[]>;
}

/**
 * Custom hook for infinite scrolling through the collection grid.
 * Merges sidebar filters and handles offset-based pagination.
 */
export function useInfiniteCollection({ viewMode, filters }: FetchItemsParams) {
  return useInfiniteQuery({
    queryKey: ["collection-grid", viewMode, filters],
    queryFn: async ({ pageParam = 0 }) => {
      const params = new URLSearchParams();
      params.append("limit", "20");
      params.append("offset", pageParam.toString());

      // Merge active sidebar filters
      Object.entries(filters).forEach(([key, val]) => {
        if (Array.isArray(val)) {
          val.forEach(v => params.append(key, v));
        } else if (val) {
          params.append(key, val.toString());
        }
      });

      const endpoint =
        viewMode === "works" ? "/works/shelf" : viewMode === "manifestations" ? "/manifestations" : "/items";
      const res = await apiClient.get<ApiResponse<any>>(`${endpoint}?${params.toString()}`);

      return res.data;
    },
    getNextPageParam: lastPage => {
      if (lastPage.pagination?.has_more) {
        return lastPage.pagination.offset + lastPage.pagination.limit;
      }
      return undefined;
    },
    initialPageParam: 0,
  });
}
