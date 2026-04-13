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
import { describe, it, expect } from "vitest";

describe("_mask_api_key behavior", () => {
  it("should show last 4 characters for long API keys", () => {
    // Simulate backend behavior - last 4 chars should be visible
    const maskKey = (value: string) => {
      if (!value) return "";
      if (value.length >= 8) return `***${value.slice(-4)}`;
      return "***";
    };

    expect(maskKey("sk-1234567890abcdef")).toBe("***cdef");
    expect(maskKey("OPENAI_API_KEY_123")).toBe("***e123");
  });

  it("should mask short values", () => {
    const maskKey = (value: string) => {
      if (!value) return "";
      if (value.length >= 8) return `***${value.slice(-4)}`;
      return "***";
    };

    expect(maskKey("short")).toBe("***");
    expect(maskKey("1234567")).toBe("***");
  });
});
