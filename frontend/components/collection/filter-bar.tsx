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
"use client";

import { X, ArrowDownUp } from "lucide-react";

/** Filter type */
export type FilterType = "status";

/** Active filter */
export interface ActiveFilter {
  type: FilterType;
  value: string;
}

/** Filter bar props */
interface FilterBarProps {
  activeFilters: ActiveFilter[];
  onRemoveFilter: (filter: ActiveFilter) => void;
  onClearAll: () => void;
  sortBy: string;
  onSortChange: (sort: string) => void;
  resultCount: number;
}

const statusLabel: Record<string, string> = {
  available: "On Shelf",
  unread: "Unread",
  reading: "Reading",
  lent: "Lent Out",
  lost: "Lost",
  wish_list: "On Wish List",
  read: "Read",
};

/**
 * Generates a label for a filter chip.
 *
 * @param filter - The active filter
 * @returns {string} The label
 */
function chipLabel(filter: ActiveFilter): string {
  if (filter.type === "status")
    return `Status: ${statusLabel[filter.value] ?? filter.value}`;
  return filter.value;
}

/**
 * Generates a color class for a filter chip.
 *
 * @param filter - The active filter
 * @returns {string} The color class
 */
function chipColor(filter: ActiveFilter): string {
  if (filter.type === "status")
    return "bg-accent/10 text-accent border-accent/20";
  return "bg-secondary text-secondary-foreground border-border";
}

/**
 * Active-filter chips + sort selector shown above the grid.
 *
 * @param root0 - The props object
 * @param root0.activeFilters - The active filters
 * @param root0.onRemoveFilter - Callback to remove a filter
 * @param root0.onClearAll - Callback to clear all filters
 * @param root0.sortBy - The current sort option
 * @param root0.onSortChange - Callback to change the sort option
 * @param root0.resultCount - The total number of results
 * @returns {JSX.Element} The component*/
export function FilterBar({
  activeFilters,
  onRemoveFilter,
  onClearAll,
  sortBy,
  onSortChange,
  resultCount,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <p className="mr-1 text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{resultCount}</span>{" "}
        items
      </p>

      {activeFilters.map((filter) => (
        <button
          key={`${filter.type}-${filter.value}`}
          onClick={() => onRemoveFilter(filter)}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:opacity-80 ${chipColor(filter)}`}
        >
          {chipLabel(filter)}
          <X className="h-3 w-3 opacity-60" />
        </button>
      ))}

      {activeFilters.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs font-medium text-accent underline-offset-2 hover:underline"
        >
          Clear all
        </button>
      )}

      <div className="ml-auto flex items-center gap-2">
        <ArrowDownUp className="h-3.5 w-3.5 text-muted-foreground" />
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value)}
          className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground outline-none transition-colors focus:border-primary"
        >
          <option value="updated">Recently updated</option>
          <option value="added">Recently added</option>
          <option value="title">Title A-Z</option>
          <option value="title-desc">Title Z-A</option>
          <option value="author">Author</option>
        </select>
      </div>
    </div>
  );
}
