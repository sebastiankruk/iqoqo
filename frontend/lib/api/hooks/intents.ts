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

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWorkIntent, setWorkIntent } from "../intents";
import { queryKeys } from "./query-keys";

/**
 * Custom hook to fetch a user's intent for a given Conceptual Work (F1).
 *
 * @param workId - Work ID
 * @returns React Query query result for the intent
 */
export function useWorkIntent(workId: number) {
  return useQuery({
    queryKey: ["workIntent", workId],
    queryFn: () => getWorkIntent(workId),
    enabled: !!workId && workId > 0,
    staleTime: 0,
  });
}

/**
 * Custom hook to set or update a user's intent for a given Conceptual Work (F1).
 *
 * @returns React Query mutation hook
 */
export function useSetWorkIntent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ workId, status }: { workId: number; status: string | null }) => {
      return setWorkIntent(workId, status);
    },
    onSuccess: (_, variables) => {
      void qc.invalidateQueries({ queryKey: ["workIntent", variables.workId] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
      void qc.invalidateQueries({ queryKey: ["items"] });
      void qc.invalidateQueries({ queryKey: ["works", "shelf"] });
      void qc.invalidateQueries({ queryKey: ["expressions", "shelf"] });
    },
  });
}
