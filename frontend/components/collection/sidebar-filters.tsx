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

import React, { useMemo, useState } from "react";
import {
  ChevronDown,
  SlidersHorizontal,
  Book,
  Music,
  Film,
  Puzzle as PuzzleIcon,
  LayoutGrid,
  Search,
  Check,
} from "lucide-react";
import type { ActiveFilter } from "./filter-bar";
import { MEDIA_HIERARCHY, CATEGORY_STATUS_MAP } from "@/types/frbr";

/** Props for SidebarFilters component */
interface SidebarFiltersProps {
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts?: Record<string, number>;
  formatCounts?: Record<string, number>;
  categoryCounts?: Record<string, number>;
  disableStatus?: boolean;
  /** Current view mode, used to contextually hide irrelevant filters */
  viewMode?: "items" | "manifestations" | "works" | "expressions";
  isLoggedIn?: boolean;
  isCurator?: boolean;
  missingCover?: boolean;
  onChangeMissingCover?: (checked: boolean) => void;
  missingId?: boolean;
  onChangeMissingId?: (checked: boolean) => void;
}

const collectionStatuses: { value: string; label: string; dot: string }[] = [
  { value: "wish_list", label: "On Wish List", dot: "bg-primary" },
  { value: "ordered", label: "Ordered", dot: "bg-orange-400" },
  { value: "available", label: "On Shelf", dot: "bg-chart-3" },
  { value: "borrowed", label: "Borrowed by me", dot: "bg-cyan-500" },
  { value: "lent", label: "Lent Out", dot: "bg-accent" },
  { value: "damaged", label: "Damaged", dot: "bg-yellow-600" },
  { value: "lost", label: "Lost", dot: "bg-destructive" },
];

const progressLabels: Record<string, { label: string; dot: string }> = {
  want_to_read: { label: "Want to Read", dot: "bg-purple-500" },
  reading: { label: "Reading", dot: "bg-green-500" },
  read: { label: "Read", dot: "bg-blue-500" },
  want_to_listen: { label: "Want to Listen", dot: "bg-purple-500" },
  listening: { label: "Listening", dot: "bg-green-500" },
  listened: { label: "Listened", dot: "bg-blue-500" },
  want_to_watch: { label: "Want to Watch", dot: "bg-purple-500" },
  watching: { label: "Watching", dot: "bg-green-500" },
  watched: { label: "Watched", dot: "bg-blue-500" },
  want_to_play: { label: "Want to Play", dot: "bg-purple-500" },
  playing: { label: "Playing", dot: "bg-green-500" },
  played: { label: "Played", dot: "bg-blue-500" },
};

const categoryIcons: Record<string, React.ReactNode> = {
  text: <Book className="h-3.5 w-3.5" />,
  music: <Music className="h-3.5 w-3.5" />,
  movie: <Film className="h-3.5 w-3.5" />,
  board_game: <LayoutGrid className="h-3.5 w-3.5" />,
  puzzle: <PuzzleIcon className="h-3.5 w-3.5" />,
};

/**
 * Checks if a filter is active.
 *
 * @param filters - The active filters
 * @param type - The filter type
 * @param value - The filter value
 * @returns {boolean} Whether the filter is active
 */
function isActive(filters: ActiveFilter[], type: string, value: string) {
  return filters.some(f => f.type === type && f.value === value);
}

/**
 * Collapsible section for the sidebar.
 *
 * @param root0 - The props object
 * @param root0.title - The section title
 * @param root0.defaultOpen - Whether the section is open by default
 * @param root0.children - The section content
 * @returns {JSX.Element} The component
 */
function AccordionSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-border pb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
      >
        {title}
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "" : "-rotate-90"}`} />
      </button>
      <div
        className={`overflow-hidden transition-all ${open ? "max-h-[500px] pb-3 opacity-100" : "max-h-0 opacity-0"}`}
      >
        {children}
      </div>
    </div>
  );
}

interface SearchableFacetProps {
  options: string[];
  activeFilters: ActiveFilter[];
  type: string;
  onToggle: (option: string) => void;
  placeholder?: string;
}

/**
 * Renders a list of facet options with a local search filter.
 *
 * @param root0 - Component props
 * @param root0.options - The options to display
 * @param root0.activeFilters - The active filters
 * @param root0.type - The filter type
 * @param root0.onToggle - Callback to toggle an option
 * @param root0.placeholder - Search placeholder
 * @returns {JSX.Element} The component
 */
export function SearchableFacet({ options, activeFilters, type, onToggle, placeholder }: SearchableFacetProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const lowerQuery = searchQuery.toLowerCase();
    return options.filter(opt => opt.toLowerCase().includes(lowerQuery));
  }, [options, searchQuery]);

  return (
    <div className="flex flex-col gap-2">
      {options.length > 5 && (
        <div className="relative sticky top-0 z-10 bg-background pb-1">
          <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder={placeholder || "Search..."}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="flex h-7 w-full rounded-md border border-input bg-transparent px-7 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
      )}

      <div className="flex flex-col gap-1 max-h-48 overflow-y-auto custom-scrollbar pr-1">
        {filteredOptions.length === 0 ? (
          <p className="text-[10px] text-muted-foreground italic py-1 px-2">No matches.</p>
        ) : (
          filteredOptions.map(option => {
            const active = isActive(activeFilters, type, option);
            return (
              <label
                key={option}
                className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1 text-sm transition-colors ${active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
              >
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => onToggle(option)}
                  className="h-3.5 w-3.5 rounded border-border accent-primary"
                />
                <span className="flex-1 truncate">{option}</span>
                {active && <Check className="h-3 w-3 text-primary" />}
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}

import { useTaxonomies } from "@/lib/api/hooks";

/**
 * Desktop sidebar with collapsible filter sections.
 *
 * @param root0 - The props object
 * @param root0.activeFilters - The active filters
 * @param root0.onToggleFilter - Callback to toggle a filter
 * @param root0.statusCounts - The counts for each status
 * @param root0.formatCounts - The counts for each format
 * @param root0.disableStatus - Whether to disable the status filter
 * @param root0.viewMode - The current view mode
 * @param root0.isLoggedIn - Whether the user is logged in
 * @param root0.categoryCounts - The counts for each category
 * @param root0.isCurator - Whether the user is a curator
 * @param root0.missingCover - Filter for items with missing cover
 * @param root0.onChangeMissingCover - Change handler for missing cover filter
 * @param root0.missingId - Filter for items with missing ID
 * @param root0.onChangeMissingId - Change handler for missing ID filter
 * @returns {JSX.Element} The component
 */
export function SidebarFilters({
  activeFilters,
  onToggleFilter,
  statusCounts = {},
  formatCounts = {},
  categoryCounts = {},
  disableStatus = false,
  viewMode = "items",
  isLoggedIn = false,
  isCurator = false,
  missingCover = false,
  onChangeMissingCover,
  onChangeMissingId,
  missingId = false,
}: SidebarFiltersProps) {
  const activeCategory = activeFilters.find(f => f.type === "category")?.value;
  const { data: taxonomies } = useTaxonomies({ scope: isLoggedIn ? "user" : "global" });

  const validProgressStatuses = activeCategory
    ? CATEGORY_STATUS_MAP[activeCategory as keyof typeof CATEGORY_STATUS_MAP] || []
    : [];

  const validFormats = activeCategory
    ? MEDIA_HIERARCHY[activeCategory as keyof typeof MEDIA_HIERARCHY]?.formats || []
    : [];

  /** True when viewing Works or Expressions – status/format don't apply at those levels */
  const isHierarchyView = viewMode === "works" || viewMode === "expressions";

  return (
    <aside className="w-full h-full overflow-y-auto pr-2 pb-20 custom-scrollbar">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-serif text-sm font-bold text-foreground">Filters</h2>
      </div>

      <AccordionSection title="Media Category">
        <div className="flex flex-col gap-1">
          {Object.entries(MEDIA_HIERARCHY).map(([id, info]) => {
            const active = isActive(activeFilters, "category", id);
            return (
              <label
                key={id}
                className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-primary/10 text-foreground ring-1 ring-primary/20" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
              >
                <input
                  type="radio"
                  name="category"
                  checked={active}
                  onChange={() => onToggleFilter({ type: "category", value: id })}
                  className="sr-only"
                />
                <span className={active ? "text-primary" : "text-muted-foreground"}>
                  {categoryIcons[id] || <LayoutGrid className="h-3.5 w-3.5" />}
                </span>
                <span className="flex-1 font-medium">{info.label}</span>
                <span className="text-xs tabular-nums text-muted-foreground mr-1">{categoryCounts[id] ?? 0}</span>
                {active && <div className="h-1.5 w-1.5 rounded-full bg-primary" />}
              </label>
            );
          })}
        </div>
      </AccordionSection>

      {taxonomies?.collections && taxonomies.collections.length > 0 && (
        <AccordionSection title="My Collections">
          <SearchableFacet
            options={taxonomies.collections}
            activeFilters={activeFilters}
            type="collection"
            onToggle={value => onToggleFilter({ type: "collection", value })}
            placeholder="Find collection..."
          />
        </AccordionSection>
      )}

      <AccordionSection title="Tags" defaultOpen={false}>
        <SearchableFacet
          options={taxonomies?.tags ?? []}
          activeFilters={activeFilters}
          type="tag"
          onToggle={value => onToggleFilter({ type: "tag", value })}
          placeholder="Find tag..."
        />
      </AccordionSection>

      <AccordionSection title="Genres" defaultOpen={false}>
        <SearchableFacet
          options={taxonomies?.genres ?? []}
          activeFilters={activeFilters}
          type="genre"
          onToggle={value => onToggleFilter({ type: "genre", value })}
          placeholder="Find genre..."
        />
      </AccordionSection>

      <AccordionSection title="Publishers" defaultOpen={false}>
        <SearchableFacet
          options={taxonomies?.publishers ?? []}
          activeFilters={activeFilters}
          type="publisher"
          onToggle={value => onToggleFilter({ type: "publisher", value })}
          placeholder="Find publisher..."
        />
      </AccordionSection>

      {!isHierarchyView && validFormats.length > 0 && (
        <AccordionSection title="Physical Kind">
          <div className="flex flex-col gap-1">
            {validFormats.map(fmt => {
              const active = isActive(activeFilters, "format", fmt.id);
              return (
                <label
                  key={fmt.id}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-accent/10 text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
                >
                  <input
                    type="radio"
                    name="format_filter"
                    checked={active}
                    onChange={() => onToggleFilter({ type: "format", value: fmt.id })}
                    className="h-4 w-4 shrink-0 rounded-full border-input text-primary shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <span className="flex-1">{fmt.label}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{formatCounts[fmt.id] ?? 0}</span>
                </label>
              );
            })}
          </div>
        </AccordionSection>
      )}

      <AccordionSection title="Collection Status">
        {isHierarchyView ? (
          <p className="px-2 py-1.5 text-xs text-muted-foreground">
            Status filters apply to physical items only. Switch to &ldquo;My Items&rdquo; view to filter by status.
          </p>
        ) : disableStatus ? (
          <p className="px-2 py-1.5 text-xs text-muted-foreground">Not applicable here.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {collectionStatuses.map(({ value, label, dot }) => {
              const active = isActive(activeFilters, "status", value);
              return (
                <label
                  key={value}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => onToggleFilter({ type: "status", value })}
                    className="h-3.5 w-3.5 rounded border-border accent-primary"
                  />
                  <span className={`h-2 w-2 rounded-full ${dot}`} />
                  <span className="flex-1">{label}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{statusCounts[value] ?? 0}</span>
                </label>
              );
            })}
          </div>
        )}
      </AccordionSection>

      {!isHierarchyView && activeCategory && validProgressStatuses.length > 0 && (
        <AccordionSection title="Progress">
          <div className="flex flex-col gap-1">
            {validProgressStatuses.map(status => {
              const info = progressLabels[status] || { label: status, dot: "bg-muted" };
              const active = isActive(activeFilters, "status", status);
              return (
                <label
                  key={status}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => onToggleFilter({ type: "status", value: status })}
                    className="h-3.5 w-3.5 rounded border-border accent-primary"
                  />
                  <span className={`h-2 w-2 rounded-full ${info.dot}`} />
                  <span className="flex-1">{info.label}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{statusCounts[status] ?? 0}</span>
                </label>
              );
            })}
          </div>
        </AccordionSection>
      )}

      {isCurator && (
        <AccordionSection title="Curation" defaultOpen={false}>
          <div className="flex flex-col gap-1">
            <label
              className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${missingCover ? "bg-muted text-foreground font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
            >
              <input
                type="checkbox"
                checked={missingCover}
                onChange={e => onChangeMissingCover?.(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-border accent-primary"
              />
              <span className="flex-1">No Cover</span>
            </label>
            <label
              className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${missingId ? "bg-muted text-foreground font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"}`}
            >
              <input
                type="checkbox"
                checked={missingId}
                onChange={e => onChangeMissingId?.(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-border accent-primary"
              />
              <span className="flex-1">No ID</span>
            </label>
          </div>
        </AccordionSection>
      )}
    </aside>
  );
}
