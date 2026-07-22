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

import { Fragment, useState, useMemo, useCallback, Suspense, useEffect, useRef } from "react";
import {
  SlidersHorizontal,
  Search,
  Library as LibraryIcon,
  BookOpen,
  Layers,
  Type,
  Users,
  Loader2,
} from "lucide-react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";
import { FilterBar, chipLabel } from "@/components/collection/filter-bar";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { MobileFilterDrawer } from "@/components/collection/mobile-filter-drawer";
import { ShareCollectionDialog } from "@/components/collection/share-collection-dialog";
import { BulkAddToolbar } from "@/components/collection/bulk-add-toolbar";
import {
  useInfiniteItems,
  useInfiniteManifestations,
  useProfile,
  useInfiniteWorksShelf,
  useInfiniteExpressionsShelf,
  useFacetStats,
} from "@/lib/api/hooks";
import type { Item, CatalogEntry } from "@/types/frbr";
import { PermissionName } from "@/lib/permissions";
import { Footer } from "@/components/dashboard/footer";
import { RoadmapView } from "@/components/collection/roadmap-view";
import { useTranslations } from "next-intl";

/**
 * A trigger component that uses IntersectionObserver to fetch more items when scrolled into view.
 *
 * @param props - Component props.
 * @param props.hasMore - Whether there are more items to load.
 * @param props.isLoadingMore - Whether items are currently being loaded.
 * @param props.onLoadMore - Callback fired when the trigger is intersected.
 * @returns Trigger component or null if no more items.
 */
function LoadMoreTrigger({
  hasMore,
  isLoadingMore,
  onLoadMore,
}: {
  hasMore: boolean;
  isLoadingMore: boolean;
  onLoadMore: () => void;
}) {
  const loadMoreRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore && onLoadMore) {
          onLoadMore();
        }
      },
      { rootMargin: "200px" }
    );
    if (loadMoreRef.current) observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, onLoadMore]);

  if (!hasMore) return null;
  return (
    <div ref={loadMoreRef} className="flex justify-center py-6 w-full col-span-full">
      {isLoadingMore ? <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /> : <div className="h-6" />}
    </div>
  );
}

/**
 * Collection browser page with filtering, sorting and pagination.
 *
 * @returns {JSX.Element} The collection page component
 */
function CollectionContent() {
  const t = useTranslations("Collection");
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Initialization: read values directly from the URL preserving 'Go back' functionality perfectly
  const initialSort = searchParams?.get("sort") || "updated";
  const initialStatuses = searchParams?.get("statuses") || "";
  const initialTags = searchParams?.get("tags") || "";
  const initialCollections = searchParams?.get("collections") || "";
  const initialGenres = searchParams?.get("genres") || "";
  const initialPublishers = searchParams?.get("publishers") || "";

  const initialCategories = searchParams?.get("category") || "";
  const initialFormats = searchParams?.get("format") || "";

  const initialFilters: ActiveFilter[] = [
    ...(initialStatuses ? initialStatuses.split(",").map(s => ({ type: "status" as const, value: s })) : []),
    ...(initialTags ? initialTags.split(",").map(s => ({ type: "tag" as const, value: s })) : []),
    ...(initialCollections ? initialCollections.split(",").map(s => ({ type: "collection" as const, value: s })) : []),
    ...(initialGenres ? initialGenres.split(",").map(s => ({ type: "genre" as const, value: s })) : []),
    ...(initialPublishers ? initialPublishers.split(",").map(s => ({ type: "publisher" as const, value: s })) : []),
    ...(initialCategories ? initialCategories.split(",").map(s => ({ type: "category" as const, value: s })) : []),
    ...(initialFormats ? initialFormats.split(",").map(s => ({ type: "format" as const, value: s })) : []),
  ];

  const initialViewMode = (searchParams?.get("view") || "items") as
    | "items"
    | "manifestations"
    | "works"
    | "expressions"
    | "roadmap";
  const initialQuery = searchParams?.get("q") ?? "";
  const initialMissingCover = searchParams?.get("missing_cover") === "true";
  const initialMissingId = searchParams?.get("missing_id") === "true";

  const [viewMode, setViewMode] = useState<"items" | "manifestations" | "works" | "expressions" | "roadmap">(
    initialViewMode
  );
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>(initialFilters);
  const [sortBy, setSortBy] = useState(initialSort);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  /** Manifestations selected for bulk-add (id → CatalogEntry) in Global Library view. */
  const [selectedManifestations, setSelectedManifestations] = useState<Map<number, CatalogEntry>>(new Map());

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [appliedQuery, setAppliedQuery] = useState(initialQuery);
  const [missingCoverOnly, setMissingCoverOnly] = useState(initialMissingCover);
  const [missingIdOnly, setMissingIdOnly] = useState(initialMissingId);

  // Keep search queries in sync if URL changes externally (e.g. from Navbar)
  const [lastUrlQuery, setLastUrlQuery] = useState(initialQuery);
  if (initialQuery !== lastUrlQuery) {
    setLastUrlQuery(initialQuery);
    setSearchQuery(initialQuery);
    setAppliedQuery(initialQuery);
  }

  // Sync viewMode when searchParams becomes available after Suspense hydration
  const [lastUrlViewMode, setLastUrlViewMode] = useState(initialViewMode);
  if (initialViewMode !== lastUrlViewMode) {
    setLastUrlViewMode(initialViewMode);
    setViewMode(initialViewMode);
  }

  // Sync filters when searchParams becomes available after Suspense hydration
  const initialFilterKey = JSON.stringify(initialFilters);
  const [lastFilterKey, setLastFilterKey] = useState(initialFilterKey);
  if (initialFilterKey !== lastFilterKey) {
    setLastFilterKey(initialFilterKey);
    setActiveFilters(initialFilters);
  }

  const limit = 20;

  const { data: profile, isLoading: isProfileLoading } = useProfile();
  const isLoggedIn = !!profile;
  const isCurator = isLoggedIn && !!profile?.permissions?.includes(PermissionName.WRITE_METADATA);

  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);
  const showClientContent = mounted && isLoggedIn;
  const showCuratorContent = mounted && isCurator;

  // Track profile state to adjust viewMode dynamically
  const [prevIsLoggedIn, setPrevIsLoggedIn] = useState<boolean | null>(null);
  if (!isProfileLoading && isLoggedIn !== prevIsLoggedIn) {
    setPrevIsLoggedIn(isLoggedIn);
    if (
      !isLoggedIn &&
      (viewMode === "items" || viewMode === "works" || viewMode === "expressions" || viewMode === "roadmap")
    ) {
      setViewMode("manifestations");
    }
  }

  const statusFilters = useMemo(() => {
    const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
    // Separate 'borrowed' virtual status from DB statuses
    return statuses.filter(s => s !== "borrowed");
  }, [activeFilters]);

  const isBorrowedFilterActive = useMemo(
    () => activeFilters.some(f => f.type === "status" && f.value === "borrowed"),
    [activeFilters]
  );

  const categoryFilters = useMemo(
    () => activeFilters.filter(f => f.type === "category").map(f => f.value),
    [activeFilters]
  );

  const formatFilters = useMemo(
    () => activeFilters.filter(f => f.type === "format").map(f => f.value),
    [activeFilters]
  );

  const tagFilters = useMemo(() => activeFilters.filter(f => f.type === "tag").map(f => f.value), [activeFilters]);
  const collectionFilters = useMemo(
    () => activeFilters.filter(f => f.type === "collection").map(f => f.value),
    [activeFilters]
  );
  const genreFilters = useMemo(() => activeFilters.filter(f => f.type === "genre").map(f => f.value), [activeFilters]);
  const publisherFilters = useMemo(
    () => activeFilters.filter(f => f.type === "publisher").map(f => f.value),
    [activeFilters]
  );

  // Automatically sync all states robustly back to the URL as they change
  useEffect(() => {
    const params = new URLSearchParams();
    if (sortBy !== "updated") params.set("sort", sortBy);

    const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
    if (statuses.length > 0) params.set("statuses", statuses.join(","));

    if (tagFilters.length > 0) params.set("tags", tagFilters.join(","));
    if (collectionFilters.length > 0) params.set("collections", collectionFilters.join(","));
    if (genreFilters.length > 0) params.set("genres", genreFilters.join(","));
    if (publisherFilters.length > 0) params.set("publishers", publisherFilters.join(","));
    if (categoryFilters.length > 0) params.set("category", categoryFilters.join(","));
    if (formatFilters.length > 0) params.set("format", formatFilters.join(","));

    if (appliedQuery) params.set("q", appliedQuery);
    if (viewMode !== "items") params.set("view", viewMode);
    if (isBorrowedFilterActive) params.set("borrowed", "true");
    if (missingCoverOnly) params.set("missing_cover", "true");
    if (missingIdOnly) params.set("missing_id", "true");

    // Replace state blocks messy rapid history buildup while keeping deep link persistency active
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [
    sortBy,
    activeFilters,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    appliedQuery,
    viewMode,
    isLoggedIn,
    isBorrowedFilterActive,
    missingCoverOnly,
    missingIdOnly,
    categoryFilters,
    formatFilters,
    pathname,
    router,
  ]);

  const {
    data: itemsData,
    isLoading: itemsLoading,
    fetchNextPage: fetchNextItems,
    hasNextPage: hasMoreItems,
    isFetchingNextPage: isFetchingMoreItems,
  } = useInfiniteItems(
    limit,
    statusFilters.length > 0 ? statusFilters : undefined,
    appliedQuery,
    sortBy,
    viewMode === "items" && isLoggedIn,
    categoryFilters.length > 0 ? categoryFilters.join(",") : undefined,
    formatFilters.length > 0 ? formatFilters.join(",") : undefined,
    isBorrowedFilterActive,
    missingCoverOnly,
    missingIdOnly,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    false
  );

  const {
    data: manifestationsData,
    isLoading: manifestationsLoading,
    fetchNextPage: fetchNextManifestations,
    hasNextPage: hasMoreManifestations,
    isFetchingNextPage: isFetchingMoreManifestations,
  } = useInfiniteManifestations(
    limit,
    appliedQuery,
    viewMode === "manifestations",
    categoryFilters.length > 0 ? categoryFilters.join(",") : undefined,
    formatFilters.length > 0 ? formatFilters.join(",") : undefined,
    missingCoverOnly,
    missingIdOnly,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    statusFilters
  );

  const {
    data: worksData,
    isLoading: worksLoading,
    fetchNextPage: fetchNextWorks,
    hasNextPage: hasMoreWorks,
    isFetchingNextPage: isFetchingMoreWorks,
  } = useInfiniteWorksShelf(
    limit,
    viewMode === "works" && isLoggedIn,
    appliedQuery,
    categoryFilters.length > 0 ? categoryFilters.join(",") : undefined,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    statusFilters.length > 0 ? statusFilters : undefined,
    formatFilters.length > 0 ? formatFilters : undefined
  );
  const {
    data: exprsData,
    isLoading: exprsLoading,
    fetchNextPage: fetchNextExprs,
    hasNextPage: hasMoreExprs,
    isFetchingNextPage: isFetchingMoreExprs,
  } = useInfiniteExpressionsShelf(
    limit,
    viewMode === "expressions" && isLoggedIn,
    appliedQuery,
    categoryFilters.length > 0 ? categoryFilters.join(",") : undefined,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    statusFilters.length > 0 ? statusFilters : undefined,
    formatFilters.length > 0 ? formatFilters : undefined
  );

  const filtersForFacets = useMemo(() => {
    const f: Record<string, string> = {};
    if (categoryFilters.length > 0) f.category = categoryFilters.join(",");
    if (formatFilters.length > 0) f.format = formatFilters.join(",");
    if (tagFilters.length > 0) f.tags = tagFilters.join(",");
    if (collectionFilters.length > 0) f.collections = collectionFilters.join(",");
    if (genreFilters.length > 0) f.genres = genreFilters.join(",");
    if (publisherFilters.length > 0) f.publishers = publisherFilters.join(",");
    if (statusFilters.length > 0) f.statuses = statusFilters.join(",");
    if (isBorrowedFilterActive) f.borrowed = "true";
    if (missingCoverOnly) f.missing_cover = "true";
    if (missingIdOnly) f.missing_id = "true";
    f.scope = isLoggedIn ? "user" : "global";
    f.view = viewMode;
    return f;
  }, [
    categoryFilters,
    formatFilters,
    tagFilters,
    collectionFilters,
    genreFilters,
    publisherFilters,
    statusFilters,
    isBorrowedFilterActive,
    missingCoverOnly,
    missingIdOnly,
    viewMode,
    isLoggedIn,
  ]);

  const { data: facetStatsData } = useFacetStats(isLoggedIn ? "user" : "global", filtersForFacets, true);

  const isLoading =
    viewMode === "roadmap"
      ? false
      : viewMode === "items"
        ? itemsLoading
        : viewMode === "manifestations"
          ? manifestationsLoading
          : viewMode === "works"
            ? worksLoading
            : exprsLoading;

  const allItems = useMemo<Array<Item | CatalogEntry>>(() => {
    if (viewMode === "items") {
      return itemsData?.pages.flatMap(page => page.data || []) ?? [];
    }
    if (viewMode === "manifestations") {
      return manifestationsData?.pages.flatMap(page => page.data || []) ?? [];
    }
    return [];
  }, [itemsData, manifestationsData, viewMode]);

  const allWorks = useMemo(() => {
    return worksData?.pages.flatMap(page => page.data || []) ?? [];
  }, [worksData]);

  const allExprs = useMemo(() => {
    return exprsData?.pages.flatMap(page => page.data || []) ?? [];
  }, [exprsData]);

  const total =
    viewMode === "works"
      ? (worksData?.pages?.[0]?.pagination?.total ?? 0)
      : viewMode === "expressions"
        ? (exprsData?.pages?.[0]?.pagination?.total ?? 0)
        : viewMode === "items"
          ? (itemsData?.pages?.[0]?.meta?.total ?? 0)
          : viewMode === "manifestations"
            ? (manifestationsData?.pages?.[0]?.meta?.total ?? 0)
            : 0;

  /** Clears all selected manifestations (e.g. after switching view mode). */
  const clearManifestationSelection = useCallback(() => {
    setSelectedManifestations(new Map());
  }, []);

  /** Toggles selection of a single manifestation, storing the full CatalogEntry. */
  const toggleManifestationSelection = useCallback(
    (id: number) => {
      // Find the CatalogEntry from the current pages of loaded manifestations
      const entry = allItems.find(item => item.id === id) as CatalogEntry | undefined;
      setSelectedManifestations(prev => {
        const next = new Map(prev);
        if (next.has(id)) {
          next.delete(id);
        } else if (entry) {
          next.set(id, entry);
        }
        return next;
      });
    },
    [allItems]
  );

  const toggleFilter = useCallback((filter: ActiveFilter) => {
    setActiveFilters(prev => {
      const exists = prev.some(f => f.type === filter.type && f.value === filter.value);
      if (exists) {
        let next = prev.filter(f => !(f.type === filter.type && f.value === filter.value));
        if (filter.type === "category") {
          const remainingCategories = next.filter(f => f.type === "category");
          if (remainingCategories.length === 0) {
            next = next.filter(f => f.type !== "format");
          }
        }
        return next;
      } else {
        return [...prev, filter];
      }
    });
  }, []);

  const removeFilter = useCallback((filter: ActiveFilter) => {
    setActiveFilters(prev => {
      let next = prev.filter(f => !(f.type === filter.type && f.value === filter.value));
      if (filter.type === "category") {
        const remainingCategories = next.filter(f => f.type === "category");
        if (remainingCategories.length === 0) {
          next = next.filter(f => f.type !== "format");
        }
      }
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setActiveFilters([]);
  }, []);

  const formatCounts = useMemo<Record<string, number>>(() => {
    return facetStatsData?.format_counts ?? ({} as Record<string, number>);
  }, [facetStatsData]);

  const categoryCounts = useMemo<Record<string, number>>(() => {
    return facetStatsData?.category_counts ?? ({} as Record<string, number>);
  }, [facetStatsData]);

  const statusCounts = useMemo<Record<string, number>>(() => {
    return facetStatsData?.status_counts ?? ({} as Record<string, number>);
  }, [facetStatsData]);

  const filteredItems = useMemo(() => {
    const items = [...allItems];
    items.sort((a, b) => {
      const ta = a.title ?? "";
      const tb = b.title ?? "";
      const aa = a.authors?.[0] ?? "";
      const ab = b.authors?.[0] ?? "";
      switch (sortBy) {
        case "title":
          return ta.localeCompare(tb);
        case "title-desc":
          return tb.localeCompare(ta);
        case "author":
          return aa.localeCompare(ab);
        case "updated": {
          const uA = (a as Item).updated_at ? new Date((a as Item).updated_at!).getTime() : 0;
          const uB = (b as Item).updated_at ? new Date((b as Item).updated_at!).getTime() : 0;
          return uB - uA;
        }
        case "added": {
          const aA = (a as Item).added_at ? new Date((a as Item).added_at!).getTime() : 0;
          const aB = (b as Item).added_at ? new Date((b as Item).added_at!).getTime() : 0;
          return aB - aA;
        }
        default:
          return 0;
      }
    });
    return items;
  }, [allItems, sortBy]);

  const ariaLiveText = useMemo(() => {
    if (activeFilters.length === 0) return `All filters cleared. ${total} results found.`;
    const filterLabels = activeFilters.map(f => chipLabel(f)).join(", ");
    return `Filtered to ${filterLabels}. ${total} results found.`;
  }, [activeFilters, total]);

  return (
    <div className="min-h-screen bg-background">
      <div aria-live="polite" className="sr-only">
        {ariaLiveText}
      </div>
      <Navbar />

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl font-bold text-foreground">
              {appliedQuery ? t("searchResults", { query: appliedQuery }) : t("title")}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {appliedQuery ? (total === 1 ? t("foundOne") : t("foundMultiple", { count: total })) : t("browseManage")}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {showClientContent && (
              <div className="flex flex-wrap items-center gap-4">
                <div role="tablist" className="flex rounded-lg border border-border bg-card p-1 shadow-sm">
                  <button
                    role="tab"
                    aria-selected={viewMode === "items"}
                    aria-label={t("tabMyItems")}
                    onClick={() => {
                      setViewMode("items");
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "items"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <BookOpen className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("tabMyItems")}</span>
                  </button>
                  <button
                    role="tab"
                    aria-selected={viewMode === "manifestations"}
                    aria-label={t("tabGlobalLibrary")}
                    onClick={() => {
                      setViewMode("manifestations");
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "manifestations"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <LibraryIcon className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("tabGlobalLibrary")}</span>
                  </button>
                  <button
                    role="tab"
                    aria-selected={viewMode === "expressions"}
                    aria-label={t("tabExpressions")}
                    onClick={() => {
                      setViewMode("expressions");
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "expressions"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <Type className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("tabExpressions")}</span>
                  </button>
                  <button
                    role="tab"
                    aria-selected={viewMode === "works"}
                    aria-label={t("tabWorks")}
                    onClick={() => {
                      setViewMode("works");
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "works"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <Layers className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("tabWorks")}</span>
                  </button>
                  <button
                    role="tab"
                    aria-selected={viewMode === "roadmap"}
                    aria-label={t("tabRoadmaps")}
                    onClick={() => {
                      setViewMode("roadmap");
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "roadmap"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <SlidersHorizontal className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("tabRoadmaps")}</span>
                  </button>
                </div>

                {/* Curation filters moved to sidebar curation facet */}
              </div>
            )}

            <form
              onSubmit={e => {
                e.preventDefault();
                setAppliedQuery(searchQuery);
              }}
              className="relative w-full sm:w-64 md:w-80"
            >
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </form>

            <button
              onClick={() => setMobileFiltersOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary lg:hidden"
            >
              <SlidersHorizontal className="h-4 w-4" />
              {t("filters")}
              {activeFilters.length > 0 && (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
                  {activeFilters.length}
                </span>
              )}
            </button>

            {showClientContent && (activeFilters.length > 0 || appliedQuery) && (
              <ShareCollectionDialog activeFilters={activeFilters} appliedQuery={appliedQuery} />
            )}
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
          <FilterBar
            activeFilters={activeFilters}
            onRemoveFilter={removeFilter}
            onClearAll={clearAll}
            sortBy={sortBy}
            onSortChange={setSortBy}
            resultCount={total}
          />
        </div>

        <div className="flex gap-8">
          <div className="hidden w-56 shrink-0 lg:block">
            <div className="sticky top-24 rounded-lg border border-border bg-card p-4 shadow-sm">
              <SidebarFilters
                activeFilters={activeFilters}
                onToggleFilter={toggleFilter}
                statusCounts={statusCounts}
                formatCounts={formatCounts}
                categoryCounts={categoryCounts}
                viewMode={viewMode}
                isLoggedIn={showClientContent}
                isCurator={showCuratorContent}
                missingCover={missingCoverOnly}
                onChangeMissingCover={setMissingCoverOnly}
                missingId={missingIdOnly}
                onChangeMissingId={setMissingIdOnly}
                tagCounts={facetStatsData?.tag_counts}
                collectionCounts={facetStatsData?.collection_counts}
                genreCounts={facetStatsData?.genre_counts}
                publisherCounts={facetStatsData?.publisher_counts}
                borrowedCount={facetStatsData?.borrowed_count}
              />
            </div>
          </div>

          <div className="min-w-0 flex-1">
            {mounted && isLoading ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={i} className="overflow-hidden rounded-lg bg-card shadow-sm">
                    <div className="aspect-[2/3] animate-pulse bg-muted" />
                    <div className="p-3">
                      <div className="h-3 animate-pulse rounded bg-muted" />
                      <div className="mt-1.5 h-2.5 w-2/3 animate-pulse rounded bg-muted" />
                    </div>
                  </div>
                ))}
              </div>
            ) : viewMode === "works" && worksData ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {allWorks.length === 0 ? (
                  <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                      <Layers className="h-7 w-7 text-muted-foreground" />
                    </div>
                    <h3 className="mt-4 font-serif text-lg font-bold text-foreground">
                      {appliedQuery ? t("noWorksMatching", { query: appliedQuery }) : t("noWorksInCollection")}
                    </h3>
                    <p className="mt-1 max-w-xs text-sm text-muted-foreground">{t("tryAdjusting")}</p>
                  </div>
                ) : (
                  allWorks.map(work => (
                    <div
                      key={work.work_id}
                      className="group flex flex-col rounded-xl border border-border bg-card shadow-sm hover:shadow-md hover:border-primary/30 transition-all overflow-hidden"
                    >
                      {/* Cover thumbnails strip – each clickable to its manifestation */}
                      <div className="flex gap-1 p-3 bg-muted/30 border-b border-border/50">
                        {work.owned_manifestations.slice(0, 4).map(m => (
                          <button
                            key={m.manifestation_id}
                            type="button"
                            onClick={() => router.push(`/manifestation/${m.manifestation_id}`)}
                            className="relative h-16 w-12 shrink-0 overflow-hidden rounded-md bg-muted shadow-sm hover:ring-2 hover:ring-primary transition-all cursor-pointer"
                            style={{
                              backgroundImage: m.cover_url ? `url(${m.cover_url})` : undefined,
                              backgroundSize: "cover",
                              backgroundPosition: "center",
                            }}
                            title={`View ${m.format} edition`}
                          >
                            {!m.cover_url && (
                              <div className="flex h-full items-center justify-center">
                                <BookOpen className="h-4 w-4 text-muted-foreground/40" />
                              </div>
                            )}
                          </button>
                        ))}
                        {work.owned_manifestations.length > 4 && (
                          <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-bold text-muted-foreground">
                            +{work.owned_manifestations.length - 4}
                          </div>
                        )}
                      </div>
                      {/* Content */}
                      <div className="flex flex-1 flex-col p-4">
                        <h3 className="font-serif font-bold text-base leading-snug text-foreground truncate group-hover:text-primary transition-colors">
                          {work.title}
                        </h3>
                        {work.creators.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {work.creators.map(c => (
                              <button
                                key={c}
                                type="button"
                                onClick={() => {
                                  setSearchQuery(c);
                                  setAppliedQuery(c);
                                  setViewMode("items");
                                }}
                                className="text-xs text-primary hover:underline font-medium"
                                title={t("browseAuthor", { author: c })}
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        )}
                        <div className="mt-3 flex items-center justify-between">
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Users className="h-3 w-3" />
                            <span>
                              {work.total_items === 1
                                ? t("itemsCountOne")
                                : t("itemsCountMultiple", { count: work.total_items })}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            {work.owned_manifestations.slice(0, 1).map(m => (
                              <Fragment key={`man-${m.manifestation_id}`}>
                                <button
                                  type="button"
                                  onClick={() => router.push(`/manifestation/${m.manifestation_id}`)}
                                  className="flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                                  title={t("viewManifestation")}
                                >
                                  <Layers className="h-3 w-3" />
                                  {t("edition")}
                                </button>
                                {m.item_id && (
                                  <button
                                    type="button"
                                    onClick={() => router.push(`/item/${m.item_id}`)}
                                    className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
                                    title={t("viewMyItem")}
                                  >
                                    <BookOpen className="h-3 w-3" />
                                    {t("myItem")}
                                  </button>
                                )}
                              </Fragment>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <LoadMoreTrigger
                  hasMore={!!hasMoreWorks}
                  isLoadingMore={isFetchingMoreWorks}
                  onLoadMore={() => hasMoreWorks && fetchNextWorks()}
                />
              </div>
            ) : viewMode === "expressions" && exprsData ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {allExprs.length === 0 ? (
                  <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                      <Type className="h-7 w-7 text-muted-foreground" />
                    </div>
                    <h3 className="mt-4 font-serif text-lg font-bold text-foreground">
                      {appliedQuery
                        ? t("noExpressionsMatching", { query: appliedQuery })
                        : t("noExpressionsInCollection")}
                    </h3>
                    <p className="mt-1 max-w-xs text-sm text-muted-foreground">{t("tryAdjusting")}</p>
                  </div>
                ) : (
                  allExprs.map(expr => (
                    <div
                      key={expr.expression_id}
                      className="group flex flex-col rounded-xl border border-border bg-card shadow-sm hover:shadow-md hover:border-primary/30 transition-all overflow-hidden"
                    >
                      {/* Cover thumbnails strip */}
                      <div className="flex gap-1 p-3 bg-muted/30 border-b border-border/50">
                        {expr.owned_manifestations.slice(0, 4).map(m => (
                          <button
                            key={m.manifestation_id}
                            type="button"
                            onClick={() => router.push(`/manifestation/${m.manifestation_id}`)}
                            className="relative h-16 w-12 shrink-0 overflow-hidden rounded-md bg-muted shadow-sm hover:ring-2 hover:ring-primary transition-all cursor-pointer"
                            style={{
                              backgroundImage: m.cover_url ? `url(${m.cover_url})` : undefined,
                              backgroundSize: "cover",
                              backgroundPosition: "center",
                            }}
                            title={`${m.format} edition`}
                          >
                            {!m.cover_url && (
                              <div className="flex h-full items-center justify-center">
                                <BookOpen className="h-4 w-4 text-muted-foreground/40" />
                              </div>
                            )}
                          </button>
                        ))}
                        {expr.owned_manifestations.length > 4 && (
                          <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-bold text-muted-foreground">
                            +{expr.owned_manifestations.length - 4}
                          </div>
                        )}
                      </div>
                      {/* Content */}
                      <div className="flex flex-1 flex-col p-4">
                        <h3 className="font-serif font-bold text-base leading-snug text-foreground truncate group-hover:text-primary transition-colors">
                          {expr.work_title}
                        </h3>
                        {expr.creators.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {expr.creators.map(c => (
                              <button
                                key={c}
                                type="button"
                                onClick={() => {
                                  setSearchQuery(c);
                                  setAppliedQuery(c);
                                  setViewMode("items");
                                }}
                                className="text-xs text-primary hover:underline font-medium"
                                title={t("browseAuthor", { author: c })}
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        )}
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          <span className="inline-flex items-center rounded-full bg-secondary/60 px-2.5 py-0.5 text-xs font-medium text-secondary-foreground capitalize">
                            {expr.content_type}
                          </span>
                          {expr.language && (
                            <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-medium text-accent uppercase">
                              {expr.language}
                            </span>
                          )}
                        </div>
                        <div className="mt-3 flex items-center justify-between">
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Users className="h-3 w-3" />
                            <span>
                              {expr.total_items === 1
                                ? t("itemsCountOne")
                                : t("itemsCountMultiple", { count: expr.total_items })}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            {expr.owned_manifestations.slice(0, 1).map(m => (
                              <Fragment key={`man-${m.manifestation_id}`}>
                                <button
                                  type="button"
                                  onClick={() => router.push(`/manifestation/${m.manifestation_id}`)}
                                  className="flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                                  title={t("viewManifestation")}
                                >
                                  <Layers className="h-3 w-3" />
                                  {t("edition")}
                                </button>
                                {m.item_id && (
                                  <button
                                    type="button"
                                    onClick={() => router.push(`/item/${m.item_id}`)}
                                    className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
                                    title={t("viewMyItem")}
                                  >
                                    <BookOpen className="h-3 w-3" />
                                    {t("myItem")}
                                  </button>
                                )}
                              </Fragment>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <LoadMoreTrigger
                  hasMore={!!hasMoreExprs}
                  isLoadingMore={isFetchingMoreExprs}
                  onLoadMore={() => hasMoreExprs && fetchNextExprs()}
                />
              </div>
            ) : viewMode === "roadmap" ? (
              <RoadmapView />
            ) : (
              <CollectionGrid
                items={filteredItems}
                isManifestationView={viewMode === "manifestations"}
                hasMore={
                  viewMode === "items" ? hasMoreItems : viewMode === "manifestations" ? hasMoreManifestations : false
                }
                isLoadingMore={
                  viewMode === "items"
                    ? isFetchingMoreItems
                    : viewMode === "manifestations"
                      ? isFetchingMoreManifestations
                      : false
                }
                onLoadMore={() => {
                  if (viewMode === "items" && hasMoreItems) fetchNextItems();
                  if (viewMode === "manifestations" && hasMoreManifestations) fetchNextManifestations();
                }}
                selectedIds={viewMode === "manifestations" ? new Set(selectedManifestations.keys()) : undefined}
                onToggleSelect={viewMode === "manifestations" && isLoggedIn ? toggleManifestationSelection : undefined}
              />
            )}
          </div>
        </div>
      </div>
      <Footer />

      {/* Floating Filter Pill */}
      {!mobileFiltersOpen && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[45] lg:hidden">
          <button
            onClick={() => setMobileFiltersOpen(true)}
            className="flex items-center gap-2 rounded-full bg-black/80 backdrop-blur-md border border-white/10 text-zinc-300 px-5 py-2.5 shadow-2xl hover:bg-black hover:text-white font-medium text-sm transition-transform active:scale-95"
            aria-label={t("filters")}
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>{t("filters")}</span>
            {activeFilters.length > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-[10px] font-bold text-black ml-1">
                {activeFilters.length}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Bulk-add toolbar – floats above footer when manifestations are selected */}
      {showClientContent && viewMode === "manifestations" && (
        <BulkAddToolbar
          selectedItems={Array.from(selectedManifestations.values())}
          onClearSelection={clearManifestationSelection}
          onSuccess={clearManifestationSelection}
        />
      )}
      <MobileFilterDrawer
        open={mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        activeFilters={activeFilters}
        onToggleFilter={toggleFilter}
        statusCounts={statusCounts}
        formatCounts={formatCounts}
        categoryCounts={categoryCounts}
        viewMode={viewMode}
        isLoggedIn={showClientContent}
        isCurator={showCuratorContent}
        missingCover={missingCoverOnly}
        onChangeMissingCover={setMissingCoverOnly}
        missingId={missingIdOnly}
        onChangeMissingId={setMissingIdOnly}
        tagCounts={facetStatsData?.tag_counts}
        collectionCounts={facetStatsData?.collection_counts}
        genreCounts={facetStatsData?.genre_counts}
        publisherCounts={facetStatsData?.publisher_counts}
      />
    </div>
  );
}

/**
 * Collection page wrapper with Suspense.
 *
 * @returns {JSX.Element} The collection page component
 */
export default function CollectionPage() {
  const t = useTranslations("Collection");
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <p className="text-muted-foreground">{t("loading")}</p>
        </div>
      }
    >
      <CollectionContent />
    </Suspense>
  );
}
