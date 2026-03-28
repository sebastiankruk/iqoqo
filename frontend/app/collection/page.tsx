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
import { Navbar } from "@/components/dashboard/navbar";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";
import { FilterBar } from "@/components/collection/filter-bar";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { MobileFilterDrawer } from "@/components/collection/mobile-filter-drawer";
import { useItems, useManifestations, useStats, useProfile } from "@/lib/api/hooks";
import type { Item, CatalogEntry } from "@/types/frbr";
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
  const initialSort = searchParams?.get("sort") || "title";
  const initialStatuses = searchParams?.get("statuses") || "";
  const initialFilters: ActiveFilter[] = initialStatuses
    ? initialStatuses.split(",").map(s => ({ type: "status", value: s }))
    : [];
  const initialViewMode = (searchParams?.get("view") || "items") as "items" | "manifestations";
  const initialQuery = searchParams?.get("q") ?? "";

  const [page, setPage] = useState(initialPage);
  const [viewMode, setViewMode] = useState<"items" | "manifestations">(initialViewMode);
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>(initialFilters);
  const [sortBy, setSortBy] = useState(initialSort);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [appliedQuery, setAppliedQuery] = useState(initialQuery);

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

  // Automatically sync all states robustly back to the URL as they change
  useEffect(() => {
    const params = new URLSearchParams();
    if (page > 1) params.set("page", page.toString());
    if (sortBy !== "title") params.set("sort", sortBy);

    const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
    if (statuses.length > 0) params.set("statuses", statuses.join(","));
    if (appliedQuery) params.set("q", appliedQuery);
    if (viewMode !== "items") params.set("view", viewMode);

    // Replace state blocks messy rapid history buildup while keeping deep link persistency active
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [page, sortBy, activeFilters, appliedQuery, viewMode, pathname, router]);

  const statusFilters = useMemo(
    () => activeFilters.filter(f => f.type === "status").map(f => f.value),
    [activeFilters]
  );

  const { data: itemsData, isLoading: itemsLoading } = useItems(
    page,
    limit,
    statusFilters.length > 0 ? statusFilters : undefined,
    appliedQuery,
    sortBy,
    viewMode === "items" && isLoggedIn
  );

  const { data: manifestationsData, isLoading: manifestationsLoading } = useManifestations(
    page,
    limit,
    appliedQuery,
    viewMode === "manifestations"
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
      return exists ? prev.filter(f => !(f.type === filter.type && f.value === filter.value)) : [...prev, filter];
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

  const statusCounts = useMemo<Record<string, number>>(() => {
    if (!statsData) return {} as Record<string, number>;
    return {
      available: statsData.items_available,
      lent: statsData.items_lent,
      lost: statsData.items_lost,
      wish_list: statsData.items_wish_list,
      reading: statsData.items_reading,
      read: statsData.items_read,
      unread: statsData.items_unread ?? statsData.to_read,
    };
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
