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

/**
 * Tests for the collection page's URL round-trip.
 *
 * These call `lib/collection-url.ts` directly. The file this replaces,
 * `__tests__/components/facet-url-sync.test.tsx`, re-implemented both directions
 * *inside the test file* and never touched the page, so sabotaging the real
 * writer (dropping `genres` from the output) left the whole frontend suite green.
 * Every assertion here is against the code that actually runs.
 */
import { describe, it, expect } from "vitest";
import {
  buildCollectionUrl,
  parseCollectionUrl,
  parseCollectionUrlScalars,
  type CollectionUrlState,
} from "@/lib/collection-url";
import type { ActiveFilter } from "@/components/collection/filter-bar";

/**
 * Build a state object with sensible defaults for the fields under test.
 *
 * @param overrides - Fields to override on top of the defaults.
 * @returns A complete state object.
 */
function state(overrides: Partial<CollectionUrlState> = {}): CollectionUrlState {
  return {
    sortBy: "updated",
    activeFilters: [],
    appliedQuery: "",
    viewMode: "items",
    missingCoverOnly: false,
    missingIdOnly: false,
    ...overrides,
  };
}

describe("buildCollectionUrl", () => {
  it("omits defaults so an unfiltered view has a clean URL", () => {
    expect(buildCollectionUrl(state())).toBe("");
  });

  it("writes a non-default sort", () => {
    expect(buildCollectionUrl(state({ sortBy: "title" }))).toBe("sort=title");
  });

  it("does not write the default sort or view", () => {
    const qs = buildCollectionUrl(state({ sortBy: "updated", viewMode: "items" }));
    expect(qs).not.toContain("sort=");
    expect(qs).not.toContain("view=");
  });

  it("writes each multi-value group comma-joined", () => {
    const activeFilters: ActiveFilter[] = [
      { type: "status", value: "available" },
      { type: "status", value: "borrowed" },
      { type: "tag", value: "horror" },
      { type: "tag", value: "classic" },
      { type: "format", value: "dvd" },
      { type: "category", value: "Movies" },
    ];
    const qs = buildCollectionUrl(state({ activeFilters }));
    const params = new URLSearchParams(qs);
    expect(params.get("statuses")).toBe("available,borrowed");
    expect(params.get("tags")).toBe("horror,classic");
    expect(params.get("format")).toBe("dvd");
    expect(params.get("category")).toBe("Movies");
  });

  it("writes every single-select facet group", () => {
    // Each of these was a separate hand-written line in the original writer; a
    // group omitted here is a filter that silently fails to appear in a share link.
    const groups: Array<[ActiveFilter["type"], string]> = [
      ["status", "statuses"],
      ["tag", "tags"],
      ["collection", "collections"],
      ["genre", "genres"],
      ["publisher", "publishers"],
      ["ownership", "ownership"],
      ["category", "category"],
      ["format", "format"],
      ["lod_authority", "lod_authority"],
      ["lod_status", "lod_status"],
    ];
    for (const [type, param] of groups) {
      const qs = buildCollectionUrl(state({ activeFilters: [{ type, value: "v" }] }));
      expect(new URLSearchParams(qs).get(param), `${type} -> ${param}`).toBe("v");
    }
  });

  it("writes the scalar toggles", () => {
    const qs = buildCollectionUrl(
      state({ appliedQuery: "noir", viewMode: "works", missingCoverOnly: true, missingIdOnly: true })
    );
    const params = new URLSearchParams(qs);
    expect(params.get("q")).toBe("noir");
    expect(params.get("view")).toBe("works");
    expect(params.get("missing_cover")).toBe("true");
    expect(params.get("missing_id")).toBe("true");
  });

  it("omits a false toggle rather than writing it", () => {
    expect(buildCollectionUrl(state({ missingCoverOnly: false }))).not.toContain("missing_cover");
  });

  it("does not emit the dead borrowed=true parameter", () => {
    // `borrowed` is a status *value*, so it rides along in statuses=borrowed.
    // The original writer also set borrowed=true, which no reader ever read.
    const qs = buildCollectionUrl(state({ activeFilters: [{ type: "status", value: "borrowed" }] }));
    expect(new URLSearchParams(qs).get("borrowed")).toBeNull();
    expect(new URLSearchParams(qs).get("statuses")).toBe("borrowed");
  });

  it("produces an empty string after clear-all", () => {
    expect(buildCollectionUrl(state({ activeFilters: [{ type: "tag", value: "x" }] }))).not.toBe("");
    expect(buildCollectionUrl(state())).toBe("");
  });
});

describe("parseCollectionUrl", () => {
  it("reads a deep link into filters", () => {
    expect(parseCollectionUrl("statuses=available,borrowed&tags=horror&format=dvd")).toEqual([
      { type: "status", value: "available" },
      { type: "status", value: "borrowed" },
      { type: "tag", value: "horror" },
      { type: "format", value: "dvd" },
    ]);
  });

  it("tolerates a leading question mark", () => {
    expect(parseCollectionUrl("?tags=horror")).toEqual([{ type: "tag", value: "horror" }]);
  });

  it("returns nothing for an absent or empty query", () => {
    expect(parseCollectionUrl(null)).toEqual([]);
    expect(parseCollectionUrl(undefined)).toEqual([]);
    expect(parseCollectionUrl("")).toEqual([]);
  });

  it("ignores empty and blank values", () => {
    expect(parseCollectionUrl("tags=")).toEqual([]);
    expect(parseCollectionUrl("tags=,,")).toEqual([]);
    expect(parseCollectionUrl("tags=horror,,classic")).toEqual([
      { type: "tag", value: "horror" },
      { type: "tag", value: "classic" },
    ]);
  });

  it("trims surrounding whitespace", () => {
    expect(parseCollectionUrl("tags=%20horror%20,%20classic%20")).toEqual([
      { type: "tag", value: "horror" },
      { type: "tag", value: "classic" },
    ]);
  });

  it("reads single-select facets as filters", () => {
    expect(parseCollectionUrl("lod_authority=viaf&lod_status=matched")).toEqual([
      { type: "lod_authority", value: "viaf" },
      { type: "lod_status", value: "matched" },
    ]);
  });

  it("ignores unrelated params", () => {
    expect(parseCollectionUrl("page=3&utm_source=newsletter")).toEqual([]);
  });
});

describe("parseCollectionUrlScalars", () => {
  it("supplies defaults when nothing is set", () => {
    expect(parseCollectionUrlScalars("")).toEqual({
      sortBy: "updated",
      viewMode: "items",
      appliedQuery: "",
      missingCoverOnly: false,
      missingIdOnly: false,
    });
  });

  it("reads every scalar", () => {
    expect(parseCollectionUrlScalars("sort=title&view=works&q=noir&missing_cover=true&missing_id=true")).toEqual({
      sortBy: "title",
      viewMode: "works",
      appliedQuery: "noir",
      missingCoverOnly: true,
      missingIdOnly: true,
    });
  });

  it("treats a non-true toggle as false", () => {
    expect(parseCollectionUrlScalars("missing_cover=1").missingCoverOnly).toBe(false);
    expect(parseCollectionUrlScalars("missing_cover=TRUE").missingCoverOnly).toBe(false);
  });
});

describe("round-trip", () => {
  it("returns the original filters after a write and a read", () => {
    const activeFilters: ActiveFilter[] = [
      { type: "status", value: "available" },
      { type: "status", value: "borrowed" },
      { type: "tag", value: "horror" },
      { type: "tag", value: "classic" },
      { type: "collection", value: "Shelves" },
      { type: "genre", value: "Jazz" },
      { type: "publisher", value: "Ace" },
      { type: "ownership", value: "owned" },
      { type: "category", value: "Movies" },
      { type: "format", value: "dvd" },
      { type: "lod_authority", value: "viaf" },
      { type: "lod_status", value: "matched" },
    ];
    const qs = buildCollectionUrl(state({ activeFilters, sortBy: "title", appliedQuery: "noir" }));
    expect(parseCollectionUrl(qs)).toEqual(activeFilters);
  });

  it("survives every filter type independently", () => {
    const types: ActiveFilter["type"][] = [
      "status",
      "tag",
      "collection",
      "genre",
      "publisher",
      "ownership",
      "category",
      "format",
      "lod_authority",
      "lod_status",
    ];
    for (const type of types) {
      const filters: ActiveFilter[] = [{ type, value: "x" }];
      expect(parseCollectionUrl(buildCollectionUrl(state({ activeFilters: filters }))), type).toEqual(filters);
    }
  });

  it("preserves the scalars too", () => {
    const original = state({
      sortBy: "title",
      viewMode: "works",
      appliedQuery: "noir",
      missingCoverOnly: true,
      missingIdOnly: true,
    });
    const qs = buildCollectionUrl(original);
    const scalars = parseCollectionUrlScalars(qs);
    expect(scalars.sortBy).toBe(original.sortBy);
    expect(scalars.viewMode).toBe(original.viewMode);
    expect(scalars.appliedQuery).toBe(original.appliedQuery);
    expect(scalars.missingCoverOnly).toBe(true);
    expect(scalars.missingIdOnly).toBe(true);
  });
});
