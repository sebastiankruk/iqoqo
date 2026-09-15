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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { getBoardgameMechanics } from "@/lib/api/boardgame";
import * as client from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

describe("getBoardgameMechanics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns board game mechanics array without double-unwrapping", async () => {
    const mockMechanics = [
      { id: "1", name: "Worker Placement", description: "Place workers on action spaces" },
      { id: "2", name: "Dice Rolling", description: "Roll dice to resolve outcomes" },
    ];
    vi.mocked(client.apiFetch).mockResolvedValue(mockMechanics);

    const result = await getBoardgameMechanics();
    expect(client.apiFetch).toHaveBeenCalledWith("/boardgame/mechanics");
    expect(result).toEqual(mockMechanics);
    expect(result).toHaveLength(2);
  });

  it("returns empty array when apiFetch returns null or undefined", async () => {
    vi.mocked(client.apiFetch).mockResolvedValue(null as any);

    const result = await getBoardgameMechanics();
    expect(result).toEqual([]);
  });
});
