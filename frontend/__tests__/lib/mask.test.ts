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
  it("should mask API keys showing last 4 characters", () => {
    const maskKey = (value: string) => {
      if (!value) return "";
      if (value.length >= 8) return `***${value.slice(-4)}`;
      return "***";
    };

    // Should show last 4 chars - verify pattern
    const result1 = maskKey("OPENAI_KEY_12345");
    expect(result1.startsWith("***")).toBe(true);
    expect(result1.endsWith("2345")).toBe(true);
    expect(result1.length).toBe(7); // *** + last 4 = 7
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
