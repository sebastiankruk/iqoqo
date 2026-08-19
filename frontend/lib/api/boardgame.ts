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

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { BoardgameMechanic } from "@/types/frbr";

/**
 * Fetch the controlled board game mechanics vocabulary from the API.
 *
 * @returns Array of board game mechanics.
 */
export async function getBoardgameMechanics(): Promise<BoardgameMechanic[]> {
  const res = await apiFetch<{ success: boolean; data: BoardgameMechanic[] }>("/boardgame/mechanics");
  return res?.data ?? [];
}

/**
 * React Query hook for fetching board game mechanics.
 *
 * @param enabled - Whether the query should run.
 * @returns Query result for board game mechanics.
 */
export function useBoardgameMechanics(enabled = true) {
  return useQuery<BoardgameMechanic[]>({
    queryKey: ["boardgame", "mechanics"],
    queryFn: getBoardgameMechanics,
    enabled,
    staleTime: 300_000,
  });
}
