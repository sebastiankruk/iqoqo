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
import { BookOpen, Loader2 } from "lucide-react";
import type { Item, ItemStatus, CatalogEntry } from "@/types/frbr";

const statusDotColor: Record<ItemStatus, string> = {
  available: "bg-chart-3",
  wish_list: "bg-primary",
  lent: "bg-accent",
  lost: "bg-destructive",
  reading: "bg-green-500",
  read: "bg-blue-500",
  unread: "bg-purple-500",
};

const statusDotTitle: Record<ItemStatus, string> = {
  available: "On Shelf",
  wish_list: "On Wish List",
  lent: "Lent Out",
  lost: "Lost",
  reading: "Reading",
  read: "Read",
  unread: "Unread",
};

/** Props for ItemCard component */
interface ItemCardProps {
  item: Item | CatalogEntry;
  variant?: "vertical" | "horizontal";
  isManifestationView?: boolean;
}

/**
 * Individual item card shown in the collection grid.
 *
 * @param root0 - The props object
 * @param root0.item - The item to display
 * @param root0.variant - The card variant
 * @param root0.isManifestationView - Whether to show the manifestation view
 * @returns {JSX.Element} The component
 */
export function ItemCard({ item, variant = "vertical", isManifestationView = false }: ItemCardProps) {
  const isCatalog = isManifestationView;

  // Narrow types safely instead of using 'any'
  const itemId = isCatalog ? (item as CatalogEntry).id : (item as Item).id;
  const manifestationId = isCatalog ? (item as CatalogEntry).id : (item as Item).manifestation_id;

  const status = isCatalog ? undefined : (item as Item).status;
  const userOwns = isCatalog ? (item as CatalogEntry).user_owns : true;

  const dotColor = status ? (statusDotColor[status] ?? "bg-muted") : "bg-muted";
  const dotTitle = status ? (statusDotTitle[status] ?? status) : "";

  // Dynamic linking based on view context
  const targetHref = isCatalog ? `/manifestation/${manifestationId}` : `/item/${itemId}`;

  // `cover_url` and `cover_status` exist on both Item and CatalogEntry
  const itemCoverUrl = item.cover_url;
  const coverStatus = item.cover_status;

  const coverUrl = itemCoverUrl
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"}${itemCoverUrl}`
    : isCatalog
      ? (item as CatalogEntry).meta?.["cover_url"] as string | undefined
      : ((item as Item).manifestation_meta?.["cover_url"] as string | undefined) ??
        ((item as Item).meta?.["cover_url"] as string | undefined);

  const hasLegacyCoverUrl = isCatalog
    ? Boolean((item as CatalogEntry).meta?.["cover_url"])
    : Boolean((item as Item).manifestation_meta?.["cover_url"]) || Boolean((item as Item).meta?.["cover_url"]);

  const isProcessing = coverStatus === "processing";
  const isGenerated = coverStatus === "ready" && !hasLegacyCoverUrl;

  // TypeScript allows accessing `title` and `authors` because they are defined on both types in the union
  const title = item.title ?? "Untitled";
  const authors = item.authors?.join(", ") ?? "Unknown author";

  if (variant === "horizontal") {
    return (
        <Link
            key={itemId}
            href={targetHref}
            className="group overflow-hidden rounded-xl bg-card shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex h-full p-5">
              <div className="flex flex-1 flex-col justify-between">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Book
                    </span>
                  </div>
                  <h3 className="font-serif text-lg font-bold leading-snug text-card-foreground">
                    {title}
                  </h3>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {authors}
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    {!isCatalog && (
                      <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">
                        {dotTitle}
                      </span>
                    )}
                    {isCatalog && userOwns && (
                      <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                        In Collection
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </Link>
    );
  }

  return (
    <Link href={targetHref} className="group block">
      <div className="overflow-hidden rounded-lg bg-card shadow-sm ring-1 ring-border/60 transition-all hover:shadow-md hover:ring-border">
        {/* Cover */}
        <div className="relative aspect-[2/3] w-full overflow-hidden bg-secondary">
          {(isProcessing || coverStatus === 'pending') && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-background/60 backdrop-blur-sm p-4 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="text-xs font-medium text-foreground">
                {coverStatus === 'pending' ? 'Generating...' : 'Processing...'}
              </span>
            </div>
          )}
          {coverUrl ? (
            <Image
              src={coverUrl}
              alt={`Cover of ${title}`}
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
              unoptimized
              className={`object-cover transition-transform duration-300 group-hover:scale-105 ${isGenerated ? "sepia-[.15]" : ""}`}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center bg-muted p-4 text-center">
              <span className="mb-2 font-serif text-sm font-bold text-muted-foreground line-clamp-3">{title}</span>
              <span className="text-xs text-muted-foreground line-clamp-2">{authors}</span>
              <BookOpen className="mt-4 h-6 w-6 text-muted-foreground/30" />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-start gap-2 px-3 py-2.5">
          {/* Status dot */}
          {!isCatalog && (
            <span
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotColor}`}
              title={dotTitle}
            />
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-snug text-foreground">
              {title}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {authors}
            </p>

            {isCatalog && userOwns && (
              <div className="mt-1.5 flex items-center gap-1 text-[10px] font-medium text-primary">
                <span className="inline-block h-3 w-3 rounded-full bg-primary/20" />
                In Collection
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
