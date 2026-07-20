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
import { useTranslations } from "next-intl";

/** Props for SidebarFilters component */
interface SidebarFiltersProps {
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts?: Record<string, number>;
  formatCounts?: Record<string, number>;
  categoryCounts?: Record<string, number>;
  /** Current view mode, used to contextually hide irrelevant filters */
  viewMode?: "items" | "manifestations" | "works" | "expressions" | "roadmap";
  isLoggedIn?: boolean;
  isCurator?: boolean;
  missingCover?: boolean;
  onChangeMissingCover?: (checked: boolean) => void;
  missingId?: boolean;
  onChangeMissingId?: (checked: boolean) => void;
  tagCounts?: Record<string, number>;
  collectionCounts?: Record<string, number>;
  genreCounts?: Record<string, number>;
  publisherCounts?: Record<string, number>;
  borrowedCount?: number;
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
  counts?: Record<string, number>;
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
 * @param root0.counts - The facet counts
 * @returns {JSX.Element} The component
 */
export function SearchableFacet({ options, activeFilters, type, onToggle, placeholder, counts }: SearchableFacetProps) {
  const t = useTranslations("CollectionFilters");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredOptions = useMemo(() => {
    // Filter out options with 0 counts unless they are currently active
    const availableOptions = options.filter(opt => {
      const active = isActive(activeFilters, type, opt);
      const count = counts?.[opt] ?? 0;
      return active || count > 0;
    });

    if (!searchQuery.trim()) return availableOptions;
    const lowerQuery = searchQuery.toLowerCase();
    return availableOptions.filter(opt => opt.toLowerCase().includes(lowerQuery));
  }, [options, searchQuery, activeFilters, type, counts]);

  return (
    <div className="flex flex-col gap-2">
      {options.length > 10 && (
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
          <p className="text-[10px] text-muted-foreground italic py-1 px-2">{t("noMatches")}</p>
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
                {counts && counts[option] !== undefined && (
                  <span className="text-[10px] tabular-nums text-muted-foreground">{counts[option]}</span>
                )}
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
 * @param root0.viewMode - The current view mode
 * @param root0.isLoggedIn - Whether the user is logged in
 * @param root0.categoryCounts - The counts for each category
 * @param root0.isCurator - Whether the user is a curator
 * @param root0.missingCover - Filter for items with missing cover
 * @param root0.onChangeMissingCover - Change handler for missing cover filter
 * @param root0.missingId - Filter for items with missing ID
 * @param root0.onChangeMissingId - Change handler for missing ID filter
 * @param root0.tagCounts - The counts for tags
 * @param root0.collectionCounts - The counts for collections
 * @param root0.genreCounts - The counts for genres
 * @param root0.publisherCounts - The counts for publishers
 * @param root0.borrowedCount - The number of borrowed items in the collection
 * @returns {JSX.Element} The component
 */
export function SidebarFilters({
  activeFilters,
  onToggleFilter,
  statusCounts = {},
  formatCounts = {},
  categoryCounts = {},
  viewMode = "items",
  isLoggedIn = false,
  isCurator = false,
  missingCover = false,
  onChangeMissingCover,
  onChangeMissingId,
  missingId = false,
  tagCounts = {},
  collectionCounts: collCountsFromProps = {},
  genreCounts = {},
  publisherCounts = {},
  borrowedCount,
}: SidebarFiltersProps) {
  const t = useTranslations("CollectionFilters");
  const activeCategories = activeFilters.filter(f => f.type === "category").map(f => f.value);

  const taxonomyScope = isLoggedIn ? "user" : "global";
  const { data: taxonomies } = useTaxonomies({
    scope: taxonomyScope,
    filters: {
      ...(activeCategories.length > 0 && { category: activeCategories[0] }),
    },
  });

  const validProgressStatuses = Array.from(
    new Set(activeCategories.flatMap(cat => CATEGORY_STATUS_MAP[cat as keyof typeof CATEGORY_STATUS_MAP] || []))
  );

  const rawFormats = activeCategories.flatMap(
    cat => (MEDIA_HIERARCHY[cat as keyof typeof MEDIA_HIERARCHY]?.formats || []) as readonly unknown[]
  ) as Array<{ id: string; label: string }>;

  const validFormats = Array.from(new Map(rawFormats.map(f => [f.id, f])).values());

  return (
    <aside className="w-full h-full overflow-y-auto pr-2 pb-20 custom-scrollbar">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-serif text-sm font-bold text-foreground">{t("title")}</h2>
      </div>

      <AccordionSection title={t("secMediaCategory")}>
        <div className="flex flex-col gap-1">
          {Object.entries(MEDIA_HIERARCHY).map(([id]) => {
            const active = isActive(activeFilters, "category", id);
            const count = categoryCounts[id] ?? 0;
            const disabled = !active && count === 0;
            return (
              <label
                key={id}
                className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-primary/10 text-foreground ring-1 ring-primary/20" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"} ${disabled ? "opacity-50" : ""}`}
              >
                <input
                  type="checkbox"
                  name="category"
                  checked={active}
                  onChange={() => onToggleFilter({ type: "category", value: id })}
                  disabled={disabled}
                  className="sr-only"
                />
                <span className={active ? "text-primary" : "text-muted-foreground"}>
                  {categoryIcons[id] || <LayoutGrid className="h-3.5 w-3.5" />}
                </span>
                <span className="flex-1 font-medium">{t(`cat_${id}`)}</span>
                <span className="text-xs tabular-nums text-muted-foreground mr-1">{count}</span>
                {active && <div className="h-1.5 w-1.5 rounded-full bg-primary" />}
              </label>
            );
          })}
        </div>
      </AccordionSection>

      {isLoggedIn &&
        taxonomies?.collections &&
        taxonomies.collections.some(
          c => (collCountsFromProps?.[c] ?? 0) > 0 || isActive(activeFilters, "collection", c)
        ) && (
          <AccordionSection title={t("secMyCollections")}>
            <SearchableFacet
              options={taxonomies.collections}
              activeFilters={activeFilters}
              type="collection"
              onToggle={value => onToggleFilter({ type: "collection", value })}
              placeholder={t("findCollection")}
              counts={collCountsFromProps}
            />
          </AccordionSection>
        )}

      {isLoggedIn &&
        taxonomies?.tags &&
        taxonomies.tags.some(t => (tagCounts?.[t] ?? 0) > 0 || isActive(activeFilters, "tag", t)) && (
          <AccordionSection title={t("secTags")} defaultOpen={false}>
            <SearchableFacet
              options={taxonomies?.tags ?? []}
              activeFilters={activeFilters}
              type="tag"
              onToggle={value => onToggleFilter({ type: "tag", value })}
              placeholder={t("findTag")}
              counts={tagCounts}
            />
          </AccordionSection>
        )}

      {taxonomies?.genres &&
        taxonomies.genres.some(g => (genreCounts?.[g] ?? 0) > 0 || isActive(activeFilters, "genre", g)) && (
          <AccordionSection title={t("secGenres")} defaultOpen={false}>
            <SearchableFacet
              options={taxonomies?.genres ?? []}
              activeFilters={activeFilters}
              type="genre"
              onToggle={value => onToggleFilter({ type: "genre", value })}
              placeholder={t("findGenre")}
              counts={genreCounts}
            />
          </AccordionSection>
        )}

      {taxonomies?.publishers &&
        taxonomies.publishers.some(p => (publisherCounts?.[p] ?? 0) > 0 || isActive(activeFilters, "publisher", p)) && (
          <AccordionSection title={t("secPublishers")} defaultOpen={false}>
            <SearchableFacet
              options={taxonomies?.publishers ?? []}
              activeFilters={activeFilters}
              type="publisher"
              onToggle={value => onToggleFilter({ type: "publisher", value })}
              placeholder={t("findPublisher")}
              counts={publisherCounts}
            />
          </AccordionSection>
        )}

      {validFormats.length > 0 && (
        <AccordionSection title={t("secPhysicalKind")}>
          <div className="flex flex-col gap-1">
            {validFormats.map(fmt => {
              const active = isActive(activeFilters, "format", fmt.id);
              const count = formatCounts[fmt.id] ?? 0;
              const disabled = !active && count === 0;
              const isUnknown = fmt.id.startsWith("unknown_");
              return (
                <label
                  key={fmt.id}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-accent/10 text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"} ${disabled ? "opacity-50" : ""}`}
                >
                  <input
                    type="checkbox"
                    name="format_filter"
                    checked={active}
                    onChange={() => onToggleFilter({ type: "format", value: fmt.id })}
                    disabled={disabled}
                    className="h-4 w-4 shrink-0 rounded border-input text-primary shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <span className={`flex-1 ${isUnknown ? "italic" : ""}`}>
                    {t(`fmt_${fmt.id}`, { defaultValue: fmt.label })}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">{count}</span>
                </label>
              );
            })}
          </div>
        </AccordionSection>
      )}

      {isLoggedIn && (
        <AccordionSection title={t("secCollectionStatus")}>
          {(function renderStatusCheckboxes() {
            return (
              <div className="flex flex-col gap-1">
                {collectionStatuses.map(({ value, label, dot }) => {
                  const active = isActive(activeFilters, "status", value);
                  const count =
                    value === "borrowed" ? (borrowedCount ?? statusCounts[value] ?? 0) : (statusCounts[value] ?? 0);
                  const disabled = !active && count === 0;
                  return (
                    <label
                      key={value}
                      className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"} ${disabled ? "opacity-50" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => onToggleFilter({ type: "status", value })}
                        disabled={disabled}
                        className="h-3.5 w-3.5 rounded border-border accent-primary"
                      />
                      <span className={`h-2 w-2 rounded-full ${dot}`} />
                      <span className="flex-1">{t(`status_${value}`, { defaultValue: label })}</span>
                      <span className="text-xs tabular-nums text-muted-foreground">{count}</span>
                    </label>
                  );
                })}
              </div>
            );
          })()}
        </AccordionSection>
      )}

      {isLoggedIn && activeCategories.length > 0 && validProgressStatuses.length > 0 && (
        <AccordionSection title={t("secProgress")}>
          <div className="flex flex-col gap-1">
            {validProgressStatuses.map(status => {
              const info = progressLabels[status] || { label: status, dot: "bg-muted" };
              const active = isActive(activeFilters, "status", status);
              const count = statusCounts[status] ?? 0;
              const disabled = !active && count === 0;
              return (
                <label
                  key={status}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"} ${disabled ? "opacity-50" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => onToggleFilter({ type: "status", value: status })}
                    disabled={disabled}
                    className="h-3.5 w-3.5 rounded border-border accent-primary"
                  />
                  <span className={`h-2 w-2 rounded-full ${info.dot}`} />
                  <span className="flex-1">{t(`progress_${status}`, { defaultValue: info.label })}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{count}</span>
                </label>
              );
            })}
          </div>
        </AccordionSection>
      )}

      {isCurator && (
        <AccordionSection title={t("secCuration")} defaultOpen={false}>
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
              <span className="flex-1">{t("noCover")}</span>
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
              <span className="flex-1">{t("noId")}</span>
            </label>
          </div>
        </AccordionSection>
      )}
    </aside>
  );
}
