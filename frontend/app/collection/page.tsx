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

import { useState, useMemo, useCallback } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Navbar } from "@/components/dashboard/navbar";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";
import { FilterBar } from "@/components/collection/filter-bar";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { MobileFilterDrawer } from "@/components/collection/mobile-filter-drawer";
import { useItems, useStats } from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

/** Collection browser page with filtering, sorting and pagination. */
export default function CollectionPage() {
  const [page, setPage] = useState(1);
  const limit = 40;

  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);
  const [sortBy, setSortBy] = useState("title");
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // Derive status filters for server-side filtering
  const statusFilters = useMemo(
    () => activeFilters.filter((f) => f.type === "status").map((f) => f.value),
    [activeFilters]
  );

  const { data, isLoading } = useItems(
    page,
    limit,
    statusFilters.length > 0 ? statusFilters : undefined
  );
  const { data: statsData } = useStats();

  const allItems = useMemo<Item[]>(() => data?.data ?? [], [data?.data]);
  const total = data?.meta?.total ?? 0;
  const pages = data?.meta?.pages ?? 1;

  const toggleFilter = useCallback((filter: ActiveFilter) => {
    setPage(1);
    setActiveFilters((prev) => {
      const exists = prev.some(
        (f) => f.type === filter.type && f.value === filter.value
      );
      return exists
        ? prev.filter(
            (f) => !(f.type === filter.type && f.value === filter.value)
          )
        : [...prev, filter];
    });
  }, []);

  const removeFilter = useCallback((filter: ActiveFilter) => {
    setPage(1);
    setActiveFilters((prev) =>
      prev.filter(
        (f) => !(f.type === filter.type && f.value === filter.value)
      )
    );
  }, []);

  const clearAll = useCallback(() => { setPage(1); setActiveFilters([]); }, []);

  // Derive per-status counts from global stats so they reflect ALL items,
  // not just the current page.
  const statusCounts = useMemo<Record<string, number>>(() => {
    if (!statsData) return {} as Record<string, number>;
    return {
      available: statsData.items_available,
      lent: statsData.items_lent,
      lost: statsData.items_lost,
      wish_list: statsData.items_wish_list,
      reading: statsData.items_reading,
      read: statsData.items_read,
    };
  }, [statsData]);

  // Status filtering is now done server-side; only sort the current page.
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
        {/* Page header */}
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="font-serif text-2xl font-bold text-foreground">
              Collection
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Browse and manage your entire library
            </p>
          </div>
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

        {/* Filter bar */}
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

        {/* Sidebar + Grid */}
        <div className="flex gap-8">
          <div className="hidden w-56 shrink-0 lg:block">
            <div className="sticky top-24 rounded-lg border border-border bg-card p-4 shadow-sm">
              <SidebarFilters
                activeFilters={activeFilters}
                onToggleFilter={toggleFilter}
                statusCounts={statusCounts}
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
              <CollectionGrid items={filteredItems} />
            )}

            {/* Pagination */}
            {pages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
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

      <footer className="mt-12 border-t border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <p className="text-xs text-muted-foreground">
            <span className="font-serif font-bold text-foreground">iqoqo</span>
            {" "}&middot;{" "}The Library of Everything
          </p>
          <p className="text-xs text-muted-foreground">
            {total} items curated with care
          </p>
        </div>
      </footer>

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
