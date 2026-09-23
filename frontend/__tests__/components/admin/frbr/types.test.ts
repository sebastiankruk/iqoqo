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
import { 
  formatKeyForDisplay, 
  transformMetaToFields, 
  transformFieldsToMeta,
  normalizeMetaValue,
  ensureArray,
  ARRAY_META_FIELDS
} from "@/components/admin/frbr/types";

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

describe("ARRAY_META_FIELDS", () => {
  it("contains expected array fields", () => {
    expect(ARRAY_META_FIELDS.has("authors")).toBe(true);
    expect(ARRAY_META_FIELDS.has("translators")).toBe(true);
    expect(ARRAY_META_FIELDS.has("tags")).toBe(true);
    expect(ARRAY_META_FIELDS.has("genres")).toBe(true);
  });

  it("does not contain non-array fields", () => {
    expect(ARRAY_META_FIELDS.has("title")).toBe(false);
    expect(ARRAY_META_FIELDS.has("isbn13")).toBe(false);
    expect(ARRAY_META_FIELDS.has("publisher")).toBe(false);
  });
});

describe("normalizeMetaValue", () => {
  it("returns string for non-array fields", () => {
    expect(normalizeMetaValue("title", "Some Title")).toBe("Some Title");
    expect(normalizeMetaValue("isbn13", "978-3-16-148410-0")).toBe("978-3-16-148410-0");
  });

  it("converts single author to array", () => {
    expect(normalizeMetaValue("authors", "Remigiusz Mróz")).toEqual(["Remigiusz Mróz"]);
  });

  it("splits comma-separated authors", () => {
    expect(normalizeMetaValue("authors", "Author1, Author2, Author3")).toEqual([
      "Author1",
      "Author2",
      "Author3",
    ]);
  });

  it("splits semicolon-separated authors", () => {
    expect(normalizeMetaValue("authors", "Author1; Author2")).toEqual(["Author1", "Author2"]);
  });

  it("handles empty string", () => {
    expect(normalizeMetaValue("authors", "")).toEqual([]);
    expect(normalizeMetaValue("authors", "   ")).toEqual([]);
  });

  it("trims whitespace from each author", () => {
    expect(normalizeMetaValue("authors", "  Author1  ,  Author2  ")).toEqual(["Author1", "Author2"]);
  });

  it("filters empty entries", () => {
    expect(normalizeMetaValue("authors", "Author1,,Author2,")).toEqual(["Author1", "Author2"]);
  });

  it("handles mixed separators", () => {
    expect(normalizeMetaValue("authors", "Author1, Author2; Author3")).toEqual([
      "Author1",
      "Author2",
      "Author3",
    ]);
  });

  it("normalizes tags field", () => {
    expect(normalizeMetaValue("tags", "fiction, sci-fi, adventure")).toEqual([
      "fiction",
      "sci-fi",
      "adventure",
    ]);
  });

  it("normalizes genres field", () => {
    expect(normalizeMetaValue("genres", "Thriller, Mystery")).toEqual(["Thriller", "Mystery"]);
  });
});

describe("ensureArray", () => {
  it("returns empty array for null/undefined", () => {
    expect(ensureArray(null)).toEqual([]);
    expect(ensureArray(undefined)).toEqual([]);
  });

  it("returns array as-is (filtered)", () => {
    expect(ensureArray(["a", "b"])).toEqual(["a", "b"]);
  });

  it("filters non-string elements from array", () => {
    expect(ensureArray(["a", null, "b", undefined, 123])).toEqual(["a", "b"]);
  });

  it("converts string to single-element array", () => {
    expect(ensureArray("Single Author")).toEqual(["Single Author"]);
  });

  it("splits comma-separated string", () => {
    expect(ensureArray("Author1, Author2")).toEqual(["Author1", "Author2"]);
  });

  it("splits semicolon-separated string", () => {
    expect(ensureArray("Author1; Author2")).toEqual(["Author1", "Author2"]);
  });

  it("returns empty array for non-string non-array", () => {
    expect(ensureArray(123)).toEqual([]);
    expect(ensureArray({})).toEqual([]);
    expect(ensureArray(true)).toEqual([]);
  });
});

describe("transformMetaToFields with arrays", () => {
  it("converts array to comma-separated string", () => {
    const meta = { authors: ["Author1", "Author2"] };
    const fields = transformMetaToFields(meta);
    expect(fields).toEqual([{ key: "authors", value: "Author1, Author2" }]);
  });

  it("converts single-element array to string", () => {
    const meta = { authors: ["Remigiusz Mróz"] };
    const fields = transformMetaToFields(meta);
    expect(fields).toEqual([{ key: "authors", value: "Remigiusz Mróz" }]);
  });

  it("converts empty array to empty string", () => {
    const meta = { authors: [] };
    const fields = transformMetaToFields(meta);
    expect(fields).toEqual([{ key: "authors", value: "" }]);
  });

  it("handles mixed array and non-array fields", () => {
    const meta = { 
      authors: ["Author1", "Author2"], 
      title: "Some Title",
      tags: ["fiction", "thriller"]
    };
    const fields = transformMetaToFields(meta);
    expect(fields).toEqual([
      { key: "authors", value: "Author1, Author2" },
      { key: "title", value: "Some Title" },
      { key: "tags", value: "fiction, thriller" },
    ]);
  });
});

describe("transformFieldsToMeta with array normalization", () => {
  it("normalizes authors field to array", () => {
    const fields = [
      { key: "authors", value: "Author1, Author2" },
      { key: "title", value: "Some Title" },
    ];
    const result = transformFieldsToMeta(fields);
    expect(result).toEqual({
      authors: ["Author1", "Author2"],
      title: "Some Title",
    });
  });

  it("handles empty authors", () => {
    const fields = [{ key: "authors", value: "" }];
    expect(transformFieldsToMeta(fields)).toEqual({ authors: [] });
  });

  it("normalizes single author to array", () => {
    const fields = [{ key: "authors", value: "Remigiusz Mróz" }];
    expect(transformFieldsToMeta(fields)).toEqual({ authors: ["Remigiusz Mróz"] });
  });

  it("normalizes tags field", () => {
    const fields = [{ key: "tags", value: "fiction, sci-fi" }];
    expect(transformFieldsToMeta(fields)).toEqual({ tags: ["fiction", "sci-fi"] });
  });

  it("preserves non-array fields as strings", () => {
    const fields = [
      { key: "isbn13", value: "978-3-16-148410-0" },
      { key: "publisher", value: "Publisher Name" },
    ];
    expect(transformFieldsToMeta(fields)).toEqual({
      isbn13: "978-3-16-148410-0",
      publisher: "Publisher Name",
    });
  });

  it("handles round-trip conversion", () => {
    const original = { 
      authors: ["Author1", "Author2"], 
      title: "Some Title",
      tags: ["fiction", "thriller"]
    };
    const fields = transformMetaToFields(original);
    const result = transformFieldsToMeta(fields);
    expect(result).toEqual(original);
  });
});
