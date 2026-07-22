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
import { MEDIA_HIERARCHY } from "@/types/taxonomy";

/**
 * Look up a human-readable label for a format ID from the media hierarchy.
 *
 * @param formatId - The raw format identifier (e.g., "unknown_video")
 * @returns The display label or undefined if not found
 */
function getFormatLabel(formatId: string): string | undefined {
  for (const category of Object.values(MEDIA_HIERARCHY)) {
    const found = category.formats.find(f => f.id === formatId);
    if (found) return found.label;
  }
  return undefined;
}

/** Filter type */
export type FilterType = "status" | "category" | "format" | "tag" | "collection" | "genre" | "publisher";

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
  wish_list: "On Wish List",
  ordered: "Ordered",
  available: "On Shelf",
  lent: "Lent Out",
  damaged: "Damaged",
  lost: "Lost",
  want_to_read: "Want to Read",
  reading: "Reading",
  read: "Read",
  want_to_listen: "Want to Listen",
  listening: "Listening",
  listened: "Listened",
  want_to_watch: "Want to Watch",
  watching: "Watching",
  watched: "Watched",
  want_to_play: "Want to Play",
  playing: "Playing",
  played: "Played",
};

/**
 * Generates a label for a filter chip.
 *
 * @param filter - The active filter
 * @returns {string} The label
 */
export function chipLabel(filter: ActiveFilter): string {
  if (filter.type === "status") return `Status: ${statusLabel[filter.value] ?? filter.value}`;
  if (filter.type === "category") return `Category: ${filter.value.replace("_", " ")}`;
  if (filter.type === "format") {
    const label = getFormatLabel(filter.value);
    return `Format: ${label ?? filter.value.replace("_", " ")}`;
  }
  if (filter.type === "tag") return `Tag: ${filter.value}`;
  if (filter.type === "collection") return `Collection: ${filter.value}`;
  if (filter.type === "genre") return `Genre: ${filter.value}`;
  if (filter.type === "publisher") return `Publisher: ${filter.value}`;
  return filter.value;
}

/**
 * Generates a color class for a filter chip.
 *
 * @param filter - The active filter
 * @returns {string} The color class
 */
function chipColor(filter: ActiveFilter): string {
  if (filter.type === "status") return "bg-accent/10 text-accent border-accent/20";
  if (filter.type === "category") return "bg-primary/10 text-primary border-primary/20";
  if (filter.type === "format") return "bg-secondary text-secondary-foreground border-border";
  if (filter.type === "tag")
    return "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-500 dark:border-blue-500/20";
  if (filter.type === "collection")
    return "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-500 dark:border-green-500/20";
  if (filter.type === "genre")
    return "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-500/10 dark:text-purple-500 dark:border-purple-500/20";
  if (filter.type === "publisher")
    return "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:text-orange-500 dark:border-orange-500/20";
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
    <div className="flex items-center gap-3 overflow-x-auto whitespace-nowrap pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <p className="mr-1 text-sm text-muted-foreground shrink-0" data-testid="result-count">
        <span className="font-semibold text-foreground">{resultCount}</span> items
      </p>

      {activeFilters.map(filter => (
        <button
          key={`${filter.type}-${filter.value}`}
          onClick={() => onRemoveFilter(filter)}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:opacity-80 shrink-0 ${chipColor(filter)}`}
        >
          {chipLabel(filter)}
          <X className="h-3 w-3 opacity-60" />
        </button>
      ))}

      {activeFilters.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs font-medium text-accent underline-offset-2 hover:underline shrink-0"
        >
          Clear all
        </button>
      )}

      <div className="ml-auto flex items-center gap-2 shrink-0">
        <ArrowDownUp className="h-3.5 w-3.5 text-muted-foreground" />
        <select
          value={sortBy}
          onChange={e => onSortChange(e.target.value)}
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
