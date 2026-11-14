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

"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Plus, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { WishlistCard } from "@/components/collection/wishlist-card";
import { useWishlist } from "@/lib/api/wishlist";

/**
 * The reader's wishlist, rendered independently of any owned Item.
 *
 * A wishlist entry is an `UserWorkIntent` and exists whether or not the reader
 * owns a copy, which is why this page is not a filtered view of the
 * collection.
 *
 * @returns The wishlist page element
 */
export default function WishlistPage() {
  const t = useTranslations("Wishlist");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [sortBy, setSortBy] = useState("updated");

  const trimmedQuery = searchQuery.trim();
  const isFiltered = Boolean(trimmedQuery || categoryFilter || sortBy !== "updated");
  const queryParams: Record<string, unknown> = { limit: 100 };
  if (trimmedQuery) queryParams.q = trimmedQuery;
  if (categoryFilter) queryParams.category = categoryFilter;
  if (sortBy !== "updated") queryParams.sort = sortBy;

  const { data, isLoading, isError } = useWishlist(queryParams);
  const items = data?.data ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl font-bold text-foreground">{t("title")}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {total === 1 ? t("itemCountOne") : t("itemCount", { count: total })}
            </p>
          </div>
          <Link
            href="/scan?policy=wishlist"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>{t("addToWishlist")}</span>
          </Link>
        </div>

        {/* Search, category filter, and sort controls */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={t("searchPlaceholder")}
              aria-label={t("searchPlaceholder")}
              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              aria-label={t("filterCategory")}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">{t("allCategories")}</option>
              <option value="text">Books &amp; Text</option>
              <option value="music">Music</option>
              <option value="movie">Movies</option>
              <option value="board_game">Board Games</option>
              <option value="puzzle">Puzzles</option>
              <option value="lego">LEGO Sets</option>
            </select>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              aria-label={t("sortBy")}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="updated">{t("sortUpdated")}</option>
              <option value="added">{t("sortAdded")}</option>
              <option value="title">{t("sortTitleAsc")}</option>
              <option value="title-desc">{t("sortTitleDesc")}</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20" aria-label="Loading wishlist">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : isError ? (
          <div className="rounded-xl border border-destructive/30 bg-card p-8 text-center text-sm text-destructive">
            {t("loadError")}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center">
            {isFiltered ? (
              <>
                <h2 className="font-serif text-lg font-bold">{t("noMatchingTitle")}</h2>
                <p className="mt-2 text-sm text-muted-foreground">{t("noMatchingDescription")}</p>
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setCategoryFilter("");
                    setSortBy("updated");
                  }}
                  className="mt-4 inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  {t("clearFilters")}
                </button>
              </>
            ) : (
              <>
                <h2 className="font-serif text-lg font-bold">{t("emptyTitle")}</h2>
                <p className="mt-2 text-sm text-muted-foreground">{t("emptyDescription")}</p>
                <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                  <Link
                    href="/scan?policy=wishlist"
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    <span>{t("addToWishlist")}</span>
                  </Link>
                  <Link
                    href="/collection?view=manifestations"
                    className="inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                  >
                    {t("browseCatalog")}
                  </Link>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {items.map(item => (
              <WishlistCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
