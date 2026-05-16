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

import { useState, useMemo, useCallback, Suspense, useEffect } from "react";
import { SlidersHorizontal, Search, Library as LibraryIcon, BookOpen } from "lucide-react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";
import { FilterBar } from "@/components/collection/filter-bar";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { MobileFilterDrawer } from "@/components/collection/mobile-filter-drawer";
import { ShareCollectionDialog } from "@/components/collection/share-collection-dialog";
import { useItems, useManifestations, useStats, useProfile } from "@/lib/api/hooks";
import type { Item, CatalogEntry } from "@/types/frbr";
import { PermissionName } from "@/lib/permissions";
import { Footer } from "@/components/dashboard/footer";

/**
 * Collection browser page with filtering, sorting and pagination.
 *
 * @returns {JSX.Element} The collection page component
 */
function CollectionContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Initialization: read values directly from the URL preserving 'Go back' functionality perfectly
  const initialPage = parseInt(searchParams?.get("page") || "1", 10) || 1;
  const initialSort = searchParams?.get("sort") || "updated";
  const initialStatuses = searchParams?.get("statuses") || "";
  const initialFilters: ActiveFilter[] = initialStatuses
    ? initialStatuses.split(",").map(s => ({ type: "status", value: s }))
    : [];
  const initialViewMode = (searchParams?.get("view") || "items") as "items" | "manifestations";
  const initialQuery = searchParams?.get("q") ?? "";
  const initialMissingCover = searchParams?.get("missing_cover") === "true";
  const initialMissingId = searchParams?.get("missing_id") === "true";

  const [page, setPage] = useState(initialPage);
  const [viewMode, setViewMode] = useState<"items" | "manifestations">(initialViewMode);
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>(initialFilters);
  const [sortBy, setSortBy] = useState(initialSort);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

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

  const limit = 40;

  const { data: profile, isLoading: isProfileLoading } = useProfile();
  const isLoggedIn = !!profile;

  // Track profile state to adjust viewMode dynamically
  const [prevIsLoggedIn, setPrevIsLoggedIn] = useState<boolean | null>(null);
  if (!isProfileLoading && isLoggedIn !== prevIsLoggedIn) {
    setPrevIsLoggedIn(isLoggedIn);
    if (!isLoggedIn && viewMode === "items") {
      setViewMode("manifestations");
      setPage(1);
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

  // Automatically sync all states robustly back to the URL as they change
  useEffect(() => {
    const params = new URLSearchParams();
    if (page > 1) params.set("page", page.toString());
    if (sortBy !== "updated") params.set("sort", sortBy);

    const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
    if (statuses.length > 0) params.set("statuses", statuses.join(","));
    if (appliedQuery) params.set("q", appliedQuery);
    if (viewMode !== "items") params.set("view", viewMode);
    if (isBorrowedFilterActive) params.set("borrowed", "true");
    if (missingCoverOnly) params.set("missing_cover", "true");
    if (missingIdOnly) params.set("missing_id", "true");

    // Replace state blocks messy rapid history buildup while keeping deep link persistency active
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [
    page,
    sortBy,
    activeFilters,
    appliedQuery,
    viewMode,
    isBorrowedFilterActive,
    missingCoverOnly,
    missingIdOnly,
    pathname,
    router,
  ]);

  const { data: itemsData, isLoading: itemsLoading } = useItems(
    page,
    limit,
    statusFilters.length > 0 ? statusFilters : undefined,
    appliedQuery,
    sortBy,
    viewMode === "items" && isLoggedIn,
    categoryFilters.length > 0 ? categoryFilters[0] : undefined,
    formatFilters.length > 0 ? formatFilters[0] : undefined,
    isBorrowedFilterActive,
    missingCoverOnly,
    missingIdOnly
  );

  const { data: manifestationsData, isLoading: manifestationsLoading } = useManifestations(
    page,
    limit,
    appliedQuery,
    viewMode === "manifestations",
    categoryFilters.length > 0 ? categoryFilters[0] : undefined,
    formatFilters.length > 0 ? formatFilters[0] : undefined,
    missingCoverOnly,
    missingIdOnly
  );

  const { data: statsData } = useStats();

  const currentData = viewMode === "items" ? itemsData : manifestationsData;
  const isLoading = viewMode === "items" ? itemsLoading : manifestationsLoading;

  const allItems = useMemo<Array<Item | CatalogEntry>>(
    () => (currentData?.data as Array<Item | CatalogEntry>) ?? [],
    [currentData?.data]
  );

  const total = currentData?.meta?.total ?? 0;
  const pages = currentData?.meta?.pages ?? 1;

  const toggleFilter = useCallback((filter: ActiveFilter) => {
    setPage(1);
    setActiveFilters(prev => {
      const exists = prev.some(f => f.type === filter.type && f.value === filter.value);
      if (exists) {
        return prev.filter(f => !(f.type === filter.type && f.value === filter.value));
      } else {
        // Enforce single-select for category and format
        if (filter.type === "category" || filter.type === "format") {
          return [...prev.filter(f => f.type !== filter.type), filter];
        }
        return [...prev, filter];
      }
    });
  }, []);

  const removeFilter = useCallback((filter: ActiveFilter) => {
    setPage(1);
    setActiveFilters(prev => prev.filter(f => !(f.type === filter.type && f.value === filter.value)));
  }, []);

  const clearAll = useCallback(() => {
    setPage(1);
    setActiveFilters([]);
  }, []);

  const formatCounts = useMemo<Record<string, number>>(() => {
    if (!statsData) return {} as Record<string, number>;
    const counts: Record<string, number> = {};
    for (const [key, value] of Object.entries(statsData)) {
      if (key.startsWith("format_")) {
        counts[key.replace("format_", "")] = value as number;
      }
    }
    return counts;
  }, [statsData]);

  const statusCounts = useMemo<Record<string, number>>(() => {
    if (!statsData) return {} as Record<string, number>;
    const counts: Record<string, number> = {};
    for (const [key, value] of Object.entries(statsData)) {
      if (key.startsWith("items_")) {
        counts[key.replace("items_", "")] = value as number;
      }
    }
    // Also add to_read alias if want_to_read is missing
    if (counts.want_to_read === undefined && statsData.to_read !== undefined) {
      counts.want_to_read = statsData.to_read;
    }
    return counts;
  }, [statsData]);

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

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl font-bold text-foreground">
              {appliedQuery ? `Search results for "${appliedQuery}"` : "Collection"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {appliedQuery ? `Found ${total} ${total === 1 ? "item" : "items"}` : "Browse and manage your library"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {isLoggedIn && (
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex rounded-lg border border-border bg-card p-1 shadow-sm">
                  <button
                    onClick={() => {
                      setViewMode("items");
                      setPage(1);
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "items"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <BookOpen className="h-4 w-4" /> My Items
                  </button>
                  <button
                    onClick={() => {
                      setViewMode("manifestations");
                      setPage(1);
                    }}
                    className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === "manifestations"
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                  >
                    <LibraryIcon className="h-4 w-4" /> Global Library
                  </button>
                </div>

                {isLoggedIn && profile?.permissions?.includes(PermissionName.WRITE_METADATA) && (
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 cursor-pointer bg-card border border-border rounded-lg px-3 py-1.5 shadow-sm hover:bg-secondary transition-colors">
                      <input
                        type="checkbox"
                        checked={missingCoverOnly}
                        onChange={() => {
                          setMissingCoverOnly(!missingCoverOnly);
                          setPage(1);
                        }}
                        className="h-4 w-4 rounded border-border accent-primary"
                      />
                      <span className="text-sm font-medium">No Cover</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer bg-card border border-border rounded-lg px-3 py-1.5 shadow-sm hover:bg-secondary transition-colors">
                      <input
                        type="checkbox"
                        checked={missingIdOnly}
                        onChange={() => {
                          setMissingIdOnly(!missingIdOnly);
                          setPage(1);
                        }}
                        className="h-4 w-4 rounded border-border accent-primary"
                      />
                      <span className="text-sm font-medium">No ID</span>
                    </label>
                  </div>
                )}
              </div>
            )}

            <form
              onSubmit={e => {
                e.preventDefault();
                setPage(1);
                setAppliedQuery(searchQuery);
              }}
              className="relative w-full sm:w-64 md:w-80"
            >
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search title, author, or ISBN..."
                className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </form>

            <button
              onClick={() => setMobileFiltersOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary lg:hidden"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Filters
              {activeFilters.length > 0 && (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
                  {activeFilters.length}
                </span>
              )}
            </button>

            {isLoggedIn && (activeFilters.length > 0 || appliedQuery) && (
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
                disableStatus={viewMode === "manifestations"}
              />
            </div>
          </div>

          <div className="min-w-0 flex-1">
            {isLoading ? (
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
            ) : (
              <CollectionGrid items={filteredItems} isManifestationView={viewMode === "manifestations"} />
            )}

            {pages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {pages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(pages, p + 1))}
                  disabled={page === pages}
                  className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
      <MobileFilterDrawer
        open={mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        activeFilters={activeFilters}
        onToggleFilter={toggleFilter}
        statusCounts={statusCounts}
        formatCounts={formatCounts}
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
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <p className="text-muted-foreground">Loading collection...</p>
        </div>
      }
    >
      <CollectionContent />
    </Suspense>
  );
}
