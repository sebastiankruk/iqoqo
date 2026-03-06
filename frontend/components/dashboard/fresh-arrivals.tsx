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

import Link from "next/link";
import { ChevronRight, BookOpen } from "lucide-react";
import { useItems } from "@/lib/api/hooks";

/** Horizontally scrollable "Fresh Arrivals" strip using live API data. */
export function FreshArrivals() {
  const { data, isLoading, isError } = useItems(1, 12);

  const items = data?.data ?? [];

  if (isError) {
    return (
      <section aria-label="Recently added items">
        <h2 className="mb-3 font-serif text-xl font-bold text-foreground">Fresh Arrivals</h2>
        <p className="text-sm text-muted-foreground">Could not load items — the API may be unavailable.</p>
      </section>
    );
  }

  return (
    <section aria-label="Recently added items">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="font-serif text-xl font-bold text-foreground">
            Fresh Arrivals
          </h2>
          <span className="hidden rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-muted-foreground sm:inline-block">
            Latest
          </span>
        </div>
        <Link
          href="/collection"
          className="flex items-center gap-1 text-sm font-medium text-accent transition-colors hover:text-accent/80"
        >
          View all
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>

      {isLoading ? (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="w-36 shrink-0 sm:w-40"
            >
              <div className="mb-3 aspect-[2/3] animate-pulse rounded-lg bg-muted shadow-md" />
              <div className="h-3 animate-pulse rounded bg-muted" />
              <div className="mt-1.5 h-2.5 w-2/3 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
          {items.map((item) => (
            <Link
              href={`/item/${item.id}`}
              key={item.id}
              className="group w-36 shrink-0 sm:w-40"
            >
              {/* Cover placeholder – real image would come from meta */}
              <div className="relative mb-3 aspect-[2/3] overflow-hidden rounded-lg shadow-md bg-secondary transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl">
                <div className="flex h-full items-center justify-center">
                  <BookOpen className="h-10 w-10 text-muted-foreground/40" />
                </div>
                <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/40 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
              <h3 className="truncate text-sm font-semibold text-card-foreground">
                {item.title ?? "Untitled"}
              </h3>
              <p className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-accent/60" />
                {item.authors?.[0] ?? "Unknown"}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
