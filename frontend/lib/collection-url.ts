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
 * Query-string round-trip for the collection page's filter state.
 *
 * This was 145 lines inline in `app/collection/page.tsx`, split across a read
 * half (ten `searchParams.get(...)` calls feeding a hand-built `ActiveFilter[]`)
 * and a write half (a `useEffect` reassembling the same query string on every
 * state change). The two halves are the same mapping viewed from opposite ends,
 * and only one of them was ever exercised: `facet-url-sync.test.tsx` re-implemented
 * both directions *locally inside the test file* and never called the page, so
 * sabotaging the real writer — dropping `genres` from the output — left all 1,236
 * frontend tests green.
 *
 * Extracting both halves into pure functions means the tests can call the code
 * that actually runs.
 *
 * `borrowed` is deliberately absent from this mapping. It is a *status value*
 * (`sidebar-filters.tsx`), not a filter type, so it already rides along in
 * `statuses=borrowed`. The old writer additionally emitted a `borrowed=true`
 * param that no reader ever read; it was dead weight in every shared link.
 */

import type { ActiveFilter, FilterType } from "@/components/collection/filter-bar";

/**
 * Filter types whose values are multi-select and therefore comma-joined.
 *
 * `lod_authority` and `lod_status` are deliberately excluded: they are
 * single-select facets, so joining them would misread any value that itself
 * contained a comma.
 */
const MULTI_VALUE_PARAMS: ReadonlyArray<readonly [FilterType, string]> = [
  ["status", "statuses"],
  ["tag", "tags"],
  ["collection", "collections"],
  ["genre", "genres"],
  ["publisher", "publishers"],
  ["ownership", "ownership"],
  ["category", "category"],
  ["format", "format"],
];

/** Single-select facets, stored under their own parameter name. */
const SINGLE_VALUE_PARAMS: ReadonlyArray<readonly [FilterType, string]> = [
  ["lod_authority", "lod_authority"],
  ["lod_status", "lod_status"],
];

/** Sort order that means "unspecified", and so is omitted from the URL. */
const DEFAULT_SORT = "updated";

/** View that means "unspecified", and so is omitted from the URL. */
const DEFAULT_VIEW = "items";

/** The full filter state this module round-trips through the query string. */
export interface CollectionUrlState {
  sortBy: string;
  activeFilters: ActiveFilter[];
  appliedQuery: string;
  viewMode: string;
  missingCoverOnly: boolean;
  missingIdOnly: boolean;
}

/**
 * Build the filter list from a URL query string.
 *
 * @param search - The query string, with or without a leading `?`.
 * @returns Filters in the canonical group order; unknown params are ignored.
 */
export function parseCollectionUrl(search: string | null | undefined): ActiveFilter[] {
  const params = new URLSearchParams(search ?? "");
  const filters: ActiveFilter[] = [];

  for (const [type, param] of MULTI_VALUE_PARAMS) {
    for (const value of splitValues(params.get(param))) {
      filters.push({ type, value });
    }
  }
  for (const [type, param] of SINGLE_VALUE_PARAMS) {
    for (const value of splitValues(params.get(param))) {
      filters.push({ type, value });
    }
  }

  return filters;
}

/**
 * Read the non-filter members of the state.
 *
 * @param search - The query string, with or without a leading `?`.
 * @returns Sort, view, applied query and the two missing-* toggles.
 */
export function parseCollectionUrlScalars(search: string | null | undefined): {
  sortBy: string;
  viewMode: string;
  appliedQuery: string;
  missingCoverOnly: boolean;
  missingIdOnly: boolean;
} {
  const params = new URLSearchParams(search ?? "");
  return {
    sortBy: params.get("sort") || DEFAULT_SORT,
    viewMode: params.get("view") || DEFAULT_VIEW,
    appliedQuery: params.get("q") ?? "",
    missingCoverOnly: params.get("missing_cover") === "true",
    missingIdOnly: params.get("missing_id") === "true",
  };
}

/**
 * Serialise filter state back to a query string.
 *
 * Defaults are omitted rather than written explicitly, so a collector's
 * unfiltered view has a clean `/collection` URL rather than a string of
 * `sort=updated&view=items`.
 *
 * @param state - The state to serialise.
 * @returns A query string without a leading `?`; empty when nothing is set.
 */
export function buildCollectionUrl(state: CollectionUrlState): string {
  const params = new URLSearchParams();

  if (state.sortBy && state.sortBy !== DEFAULT_SORT) {
    params.set("sort", state.sortBy);
  }
  if (state.viewMode && state.viewMode !== DEFAULT_VIEW) {
    params.set("view", state.viewMode);
  }
  if (state.appliedQuery) {
    params.set("q", state.appliedQuery);
  }
  if (state.missingCoverOnly) {
    params.set("missing_cover", "true");
  }
  if (state.missingIdOnly) {
    params.set("missing_id", "true");
  }

  for (const [type, param] of [...MULTI_VALUE_PARAMS, ...SINGLE_VALUE_PARAMS]) {
    const values = state.activeFilters.filter(f => f.type === type).map(f => f.value);
    if (values.length > 0) {
      params.set(param, values.join(","));
    }
  }

  return params.toString();
}

/**
 * Split a comma-joined parameter into its values, discarding blanks.
 *
 * @param raw - The raw parameter value.
 * @returns Trimmed, non-empty values.
 */
function splitValues(raw: string | null): string[] {
  if (!raw) {
    return [];
  }
  return raw
    .split(",")
    .map(v => v.trim())
    .filter(v => v.length > 0);
}
