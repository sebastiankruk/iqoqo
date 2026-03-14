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
import Image from "next/image";
import { ChevronRight, BookOpen, Loader2 } from "lucide-react";
import { useItems, useRecentManifestations } from "@/lib/api/hooks";

/** Horizontally scrollable "Fresh Arrivals" strip using live API data. */
interface FreshArrivalsProps {
  publicMode?: boolean;
}

interface ArrivalItem {
  id: number;
  title?: string;
  author?: string;
  authors?: string[];
}

export function FreshArrivals({ publicMode = false }: FreshArrivalsProps) {
  const { data: itemsEnvelope, isLoading: itemsLoading, isError: itemsError } = useItems(1, 12);
  const { data: recentManifestations, isLoading: manifLoading, isError: manifError } = useRecentManifestations(12);

  const isLoading = publicMode ? manifLoading : itemsLoading;
  const isError = publicMode ? manifError : itemsError;
  const items = (publicMode ? (recentManifestations ?? []) : (itemsEnvelope?.data ?? [])) as ArrivalItem[];

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
          {items.map((item: any) => {
            const coverUrl = item.cover_path
              ? `/api${item.cover_path}`
              : (item.manifestation_meta?.["cover_url"] as string | undefined) ??
                (item.meta?.["cover_url"] as string | undefined);

            const hasLegacyCoverUrl =
              Boolean(item.manifestation_meta?.["cover_url"] as string | undefined) ||
              Boolean(item.meta?.["cover_url"] as string | undefined);

            const isProcessing = item.cover_status === "processing";
            const isGenerated = item.cover_status === "ready" && !hasLegacyCoverUrl;

            return (
              <Link
                href={`/item/${item.id}`}
                key={item.id}
                className="group w-36 shrink-0 sm:w-40"
              >
                <div className="relative mb-3 aspect-[2/3] overflow-hidden rounded-lg shadow-md bg-secondary transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl">
                  
                  {(isProcessing || item.cover_status === "pending") && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-background/60 backdrop-blur-sm p-4 text-center">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      <span className="text-xs font-medium text-foreground">
                        {item.cover_status === "pending" ? "Generating..." : "Processing..."}
                      </span>
                    </div>
                  )}

                  {coverUrl ? (
                    <Image
                      src={coverUrl}
                      alt={`Cover of ${item.title ?? "Untitled"}`}
                      fill
                      sizes="(max-width: 640px) 144px, 160px"
                      unoptimized
                      className={`object-cover transition-transform duration-300 group-hover:scale-105 ${isGenerated ? "sepia-[.15]" : ""}`}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <BookOpen className="h-10 w-10 text-muted-foreground/40" />
                    </div>
                  )}
                  
                  <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/40 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                </div>
                <h3 className="truncate text-sm font-semibold text-card-foreground">
                  {item.title ?? "Untitled"}
                </h3>
                <p className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                  <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-accent/60" />
                  {item.author ?? item.authors?.[0] ?? "Unknown"}
                </p>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}