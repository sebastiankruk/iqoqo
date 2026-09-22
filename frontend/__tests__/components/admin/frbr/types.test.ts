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
import { formatKeyForDisplay, transformMetaToFields, transformFieldsToMeta } from "@/components/admin/frbr/types";

describe("formatKeyForDisplay", () => {
  it("converts snake_case to Title Case", () => {
    expect(formatKeyForDisplay("original_language")).toBe("Original Language");
  });

  it("converts camelCase to Title Case", () => {
    expect(formatKeyForDisplay("contentType")).toBe("Content Type");
  });

  it("handles single word keys", () => {
    expect(formatKeyForDisplay("title")).toBe("Title");
  });

  it("handles empty string", () => {
    expect(formatKeyForDisplay("")).toBe("");
  });

  it("handles mixed snake_case and camelCase", () => {
    expect(formatKeyForDisplay("publication_date")).toBe("Publication Date");
  });

  it("handles already formatted keys", () => {
    expect(formatKeyForDisplay("ISBN")).toBe("ISBN");
  });
});

describe("transformMetaToFields", () => {
  it("converts a metadata object to key-value pairs", () => {
    const meta = { pages: "412", type: "Book" };
    const result = transformMetaToFields(meta);
    expect(result).toEqual([
      { key: "pages", value: "412" },
      { key: "type", value: "Book" },
    ]);
  });

  it("returns empty array for null", () => {
    expect(transformMetaToFields(null)).toEqual([]);
  });

  it("returns empty array for undefined", () => {
    expect(transformMetaToFields(undefined)).toEqual([]);
  });

  it("returns empty array for empty object", () => {
    expect(transformMetaToFields({})).toEqual([]);
  });

  it("converts non-string values to strings", () => {
    const meta = { count: 42, active: true, nothing: null };
    const result = transformMetaToFields(meta);
    expect(result).toEqual([
      { key: "count", value: "42" },
      { key: "active", value: "true" },
      { key: "nothing", value: "" },
    ]);
  });

  it("handles non-object input gracefully", () => {
    expect(transformMetaToFields("string" as any)).toEqual([]);
    expect(transformMetaToFields(42 as any)).toEqual([]);
  });
});

describe("transformFieldsToMeta", () => {
  it("converts key-value pairs back to a metadata object", () => {
    const fields = [
      { key: "pages", value: "412" },
      { key: "type", value: "Book" },
    ];
    expect(transformFieldsToMeta(fields)).toEqual({ pages: "412", type: "Book" });
  });

  it("skips fields with empty keys", () => {
    const fields = [
      { key: "", value: "ignored" },
      { key: "  ", value: "also ignored" },
      { key: "valid", value: "kept" },
    ];
    expect(transformFieldsToMeta(fields)).toEqual({ valid: "kept" });
  });

  it("returns empty object for empty array", () => {
    expect(transformFieldsToMeta([])).toEqual({});
  });

  it("trims whitespace from keys", () => {
    const fields = [{ key: "  pages  ", value: "412" }];
    expect(transformFieldsToMeta(fields)).toEqual({ pages: "412" });
  });

  it("handles duplicate keys by overwriting", () => {
    const fields = [
      { key: "type", value: "Book" },
      { key: "type", value: "Audiobook" },
    ];
    expect(transformFieldsToMeta(fields)).toEqual({ type: "Audiobook" });
  });
});
