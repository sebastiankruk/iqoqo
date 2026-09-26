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

import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/client";
import { deleteWorkIntent } from "@/lib/api/intents";

describe("deleteWorkIntent", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("accepts a successful null-status payload", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: { success: true, data: { status: null }, error: null },
    } as never);

    await expect(deleteWorkIntent(42)).resolves.toBeNull();
    expect(apiClient.delete).toHaveBeenCalledWith("/works/42/intent");
  });

  it("rejects an unsuccessful response", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: { success: false, data: null, error: "Intent could not be deleted" },
    } as never);

    await expect(deleteWorkIntent(42)).rejects.toThrow("Intent could not be deleted");
  });
});
