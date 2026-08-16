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

import { useItems } from "@/lib/api/hooks";
import Link from "next/link";
import { ItemCard } from "../collection/item-card";
import { useTranslations } from "next-intl";

/**
 * "Current Context" section – shows items on the wish list ("On Wish List") and currently reading ("Reading").
 * Falls back to a placeholder card if none exist.
 *
 * @returns {JSX.Element} The component
 */
export function CurrentContext() {
  const t = useTranslations("CurrentContext");
  const { data: readingData, isLoading: isLoadingReading } = useItems(1, 10, ["reading"]);
  const { data: wishListData, isLoading: isLoadingWishList } = useItems(1, 10, ["wish_list"]);

  const readingItems = readingData?.data?.filter(item => item.status === "reading") ?? [];
  const wishListItems = wishListData?.data?.filter(item => item.collection_status === "wish_list") ?? [];
  const isLoading = isLoadingReading || isLoadingWishList;

  if (isLoading) {
    return (
      <section aria-label={t("ariaLabelActive")}>
        <h2 className="mb-5 font-serif text-xl font-bold text-foreground">{t("titleBoth")}</h2>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {[0, 1].map(i => (
            <div key={i} className="h-40 animate-pulse rounded-xl bg-card shadow-sm" />
          ))}
        </div>
      </section>
    );
  }

  if (readingItems.length === 0 && wishListItems.length === 0) {
    return (
      <section aria-label={t("ariaLabelActive")}>
        <div className="mb-5 flex items-center gap-2">
          <h2 className="font-serif text-xl font-bold text-foreground">{t("titleBoth")}</h2>
        </div>
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {t("emptyState")}
            <Link href="/collection" className="text-accent underline-offset-2 hover:underline">
              {t("browseCollection")}
            </Link>
            {t("toAddItems")}
          </p>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-8">
      {/* Currently Reading Section - Only renders if there are items */}
      {readingItems.length > 0 && (
        <section aria-label={t("ariaLabelReading")}>
          <div className="mb-5 flex items-center gap-2">
            <h2 className="font-serif text-xl font-bold text-foreground">{t("titleReading")}</h2>
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
              {readingItems.length} {t("active")}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {readingItems.map(item => (
              <ItemCard key={item.id} item={item} variant="horizontal" />
            ))}
          </div>
        </section>
      )}

      {/* Up Next Section - Only renders if there are items */}
      {wishListItems.length > 0 && (
        <section aria-label={t("ariaLabelWishList")}>
          <div className="mb-5 flex items-center gap-2">
            <h2 className="font-serif text-xl font-bold text-foreground">{t("titleWishList")}</h2>
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
              {wishListItems.length} {t("active")}
            </span>
          </div>

          <div className="flex gap-5 overflow-x-auto flex-nowrap pb-2 sm:grid sm:grid-cols-1 lg:grid-cols-2 sm:pb-0 sm:overflow-visible">
            {wishListItems.map(item => (
              <div key={item.id} className="min-w-[280px] shrink-0 sm:min-w-0 sm:shrink">
                <ItemCard item={item} variant="horizontal" />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
