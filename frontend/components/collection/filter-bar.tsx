"use client";

import { X, ArrowDownUp } from "lucide-react";

export type FilterType = "status";

export interface ActiveFilter {
  type: FilterType;
  value: string;
}

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
  shelf: "On Shelf",
  reading: "Reading",
  lent: "Lent Out",
  lost: "Lost",
};

function chipLabel(filter: ActiveFilter): string {
  if (filter.type === "status")
    return `Status: ${statusLabel[filter.value] ?? filter.value}`;
  return filter.value;
}

function chipColor(filter: ActiveFilter): string {
  if (filter.type === "status")
    return "bg-accent/10 text-accent border-accent/20";
  return "bg-secondary text-secondary-foreground border-border";
}

/** Active-filter chips + sort selector shown above the grid. */
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
          <option value="title">Title A-Z</option>
          <option value="title-desc">Title Z-A</option>
          <option value="author">Author</option>
        </select>
      </div>
    </div>
  );
}
