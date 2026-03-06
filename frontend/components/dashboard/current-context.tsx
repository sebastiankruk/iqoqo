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

/**
 * "Current Context" section – shows items on the wish list ("On Wish List") and currently reading ("Reading").
 * Falls back to a placeholder card if none exist.
 */
export function CurrentContext() {
  const { data, isLoading } = useItems(1, 10, ["wish_list", "reading"]);

  const readingItems =
    data?.data?.filter((item) => item.status === "reading") ?? [];
  const wishListItems =
    data?.data?.filter((item) => item.status === "wish_list") ?? [];

  if (isLoading) {
    return (
      <section aria-label="Currently active items">
        <h2 className="mb-5 font-serif text-xl font-bold text-foreground">
          Currently Reading and Wish List
        </h2>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-xl bg-card shadow-sm"
            />
          ))}
        </div>
      </section>
    );
  }

  if (readingItems.length === 0 && wishListItems.length === 0) {
    return (
      <section aria-label="Currently active items">
        <div className="mb-5 flex items-center gap-2">
          <h2 className="font-serif text-xl font-bold text-foreground">
            Currently Reading and Wish List
          </h2>
        </div>
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Your  &ldquo;Currently Reading and Wish List&rdquo; is empty.{" "}
            <Link href="/collection" className="text-accent underline-offset-2 hover:underline">
              Browse your collection
            </Link>{" "}
            to add items.
          </p>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-8">
      {/* Currently Reading Section - Only renders if there are items */}
      {readingItems.length > 0 && (
        <section aria-label="Currently reading items">
          <div className="mb-5 flex items-center gap-2">
            <h2 className="font-serif text-xl font-bold text-foreground">
              Currently Reading
            </h2>
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
              {readingItems.length} active
            </span>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {readingItems.map((item) => (
              <ItemCard key={item.id} item={item} variant="horizontal" />
            ))}
          </div>
        </section>
      )}

      {/* Up Next Section - Only renders if there are items */}
      {wishListItems.length > 0 && (
        <section aria-label="Wish list items">
          <div className="mb-5 flex items-center gap-2">
            <h2 className="font-serif text-xl font-bold text-foreground">
              Wish List
            </h2>
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
              {wishListItems.length} active
            </span>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {wishListItems.map((item) => (
              <ItemCard key={item.id} item={item} variant="horizontal" />
            ))}
          </div>
        </section>
      )}

    </div>


  );
}
