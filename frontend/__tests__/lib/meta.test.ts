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
import { readMeta, readMetaChain, hasMeta, hasMetaChain } from "@/lib/meta";

describe("readMeta", () => {
  it("reads the canonical lowercase spelling first", () => {
    expect(readMeta({ format: "Vinyl" }, "format")).toBe("Vinyl");
  });

  it("falls back to the capitalised spelling", () => {
    expect(readMeta({ Format: "Vinyl" }, "format")).toBe("Vinyl");
  });

  it("prefers the canonical spelling when both are present", () => {
    expect(readMeta({ format: "Vinyl", Format: "CD" }, "format")).toBe("Vinyl");
  });

  it("skips an empty string rather than returning it", () => {
    // An upstream writing `"format": ""` must fall through, not render blank.
    expect(readMeta({ format: "", Format: "CD" }, "format")).toBe("CD");
  });

  it("skips null and undefined values", () => {
    expect(readMeta({ year: null, Year: 1994 }, "year")).toBe(1994);
  });

  it("returns undefined when no spelling carries a value", () => {
    expect(readMeta({ Format: "Vinyl" }, "year")).toBeUndefined();
    expect(readMeta({}, "title")).toBeUndefined();
  });

  it("treats a missing, null or undefined meta object as no metadata", () => {
    expect(readMeta(undefined, "format")).toBeUndefined();
    expect(readMeta(null, "format")).toBeUndefined();
  });

  it("preserves falsy-but-meaningful values such as 0", () => {
    expect(readMeta({ pages: 0, Pages: 300 }, "pages")).toBe(0);
  });

  it("does not coerce the returned type", () => {
    const genres = ["Rock", "Jazz"];
    expect(readMeta<string[]>({ categories: genres }, "categories")).toBe(genres);
  });

  it("resolves author and authors to each other in either direction", () => {
    expect(readMeta({ author: "A" }, "authors")).toBe("A");
    expect(readMeta({ authors: "B" }, "author")).toBe("B");
    expect(readMeta({ Author: "C" }, "authors")).toBe("C");
  });

  it("resolves publisher from the label spelling Discogs uses", () => {
    expect(readMeta({ label: "Blue Note" }, "publisher")).toBe("Blue Note");
    expect(readMeta({ Publisher: "Ace" }, "publisher")).toBe("Ace");
  });

  it("prefers publisher over label when both are present", () => {
    // ItemHeader reads publisher first; ExtendedMetadata deliberately does not.
    // See LABEL_PUBLISHER_KEYS in extended-metadata.tsx.
    expect(readMeta({ label: "Blue Note", publisher: "EMI" }, "publisher")).toBe("EMI");
  });
});

describe("readMetaChain", () => {
  it("reads the first present key in the given order", () => {
    expect(readMetaChain({ b: 2, a: 1 }, ["a", "b"])).toBe(1);
  });

  it("skips empty strings", () => {
    expect(readMetaChain({ a: "", b: 2 }, ["a", "b"])).toBe(2);
  });

  it("returns undefined when no key carries a value", () => {
    expect(readMetaChain({ a: "" }, ["a", "b"])).toBeUndefined();
  });

  it("tolerates a missing meta object", () => {
    expect(readMetaChain(undefined, ["a"])).toBeUndefined();
  });
});

describe("hasMeta / hasMetaChain", () => {
  it("agrees with the matching reader", () => {
    for (const meta of [{ format: "Vinyl" }, { Format: "Vinyl" }, { format: "" }, {}, undefined]) {
      const present = hasMeta(meta, "format");
      expect(present, JSON.stringify(meta)).toBe(readMeta(meta, "format") !== undefined);
    }
  });

  it("is false for a key holding only an empty string", () => {
    expect(hasMeta({ format: "" }, "format")).toBe(false);
    expect(hasMetaChain({ catalog_number: "" }, ["catalog_number"])).toBe(false);
  });

  it("is true when any spelling in the chain carries a value", () => {
    expect(hasMetaChain({ "Matrix / Runout": "L-12345" }, ["matrix_number", "Matrix / Runout"])).toBe(true);
  });
});
