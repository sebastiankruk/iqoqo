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
import { useRouter } from "next/navigation";
import { BookOpen, Disc, Loader2, Film, Dices, Puzzle, EyeOff } from "lucide-react";
import type { Item, CatalogEntry } from "@/types/frbr";
import { isAudioMedia, getCoverUrl, getCoverTimestamp } from "@/lib/utils";

const statusDotColor: Record<string, string> = {
  available: "bg-chart-3",
  wish_list: "bg-primary",
  lent: "bg-accent",
  lost: "bg-destructive",
  ordered: "bg-amber-400",
  damaged: "bg-orange-600",
  reading: "bg-green-500",
  read: "bg-blue-500",
  unread: "bg-zinc-400",
  want_to_read: "bg-primary",
  listening: "bg-teal-500",
  listened: "bg-cyan-500",
  want_to_listen: "bg-sky-400",
  watching: "bg-indigo-500",
  watched: "bg-violet-500",
  want_to_watch: "bg-purple-500",
  played: "bg-rose-500",
  playing: "bg-pink-500",
};

const statusDotTitle: Record<string, string> = {
  available: "On Shelf",
  wish_list: "On Wish List",
  lent: "Lent Out",
  lost: "Lost",
  ordered: "Ordered",
  damaged: "Damaged",
  reading: "Reading",
  read: "Read",
  unread: "Unread",
  want_to_read: "Want to Read",
  listening: "Listening",
  listened: "Listened",
  want_to_listen: "Want to Listen",
  watching: "Watching",
  watched: "Watched",
  want_to_watch: "Want to Watch",
  played: "Played",
  playing: "Playing",
};

interface ItemCardProps {
  item: Item | CatalogEntry;
  variant?: "vertical" | "horizontal";
  isManifestationView?: boolean;
}

/**
 * ItemCard displays an item card with cover art, titles, creators, status dots,
 * and quantity indicators. Supports vertical and horizontal layout variants.
 *
 * @param props - Component properties.
 * @param props.item - The Item or CatalogEntry to display.
 * @param props.variant - The layout variant ("vertical" or "horizontal").
 * @param props.isManifestationView - Flag indicating if this is grouped manifestation view.
 * @returns An interactive card component linked to detail pages.
 */
export function ItemCard({ item, variant = "vertical", isManifestationView = false }: ItemCardProps) {
  const router = useRouter();
  const isCatalog = isManifestationView;

  const itemId = isCatalog ? (item as CatalogEntry).id : (item as Item).id;
  const manifestationId = isCatalog ? (item as CatalogEntry).id : (item as Item).manifestation_id;

  const progressStatus = isCatalog ? undefined : (item as Item).status;
  const collectionStatus = isCatalog ? undefined : (item as Item).collection_status;
  const status = collectionStatus && collectionStatus !== "available" ? collectionStatus : progressStatus;

  const userOwns = isCatalog ? (item as CatalogEntry).user_owns : (item as Item).is_owner;
  const isBorrowed = !isCatalog && (item as Item).is_borrowed;

  const quantity = (item as (Item | CatalogEntry) & { _quantity?: number })._quantity || 1;

  const dotColor = status ? (statusDotColor[status] ?? "bg-muted") : "bg-muted";
  const dotTitle = status ? (statusDotTitle[status] ?? status) : "";
  const targetHref = isCatalog ? `/manifestation/${manifestationId}` : `/item/${itemId}`;

  const itemCoverUrl = item.cover_url;
  const coverStatus = item.cover_status;
  const tMeta = isCatalog ? (item as CatalogEntry).meta : (item as Item).manifestation_meta || (item as Item).meta;
  const timestamp = getCoverTimestamp(tMeta);

  const coverUrl =
    getCoverUrl(itemCoverUrl || undefined, timestamp) ||
    (isCatalog
      ? ((item as CatalogEntry).meta?.["cover_url"] as string | undefined)
      : (((item as Item).manifestation_meta?.["cover_url"] as string | undefined) ??
        ((item as Item).meta?.["cover_url"] as string | undefined)));

  const hasLegacyCoverUrl = isCatalog
    ? Boolean((item as CatalogEntry).meta?.["cover_url"])
    : Boolean((item as Item).manifestation_meta?.["cover_url"]) || Boolean((item as Item).meta?.["cover_url"]);

  const isProcessing = coverStatus === "processing";
  const isGenerated = coverStatus === "ready" && !hasLegacyCoverUrl;

  const format = isCatalog
    ? ((item as CatalogEntry).meta?.["format"] as string | undefined)
    : (((item as Item).manifestation_meta?.["format"] as string | undefined) ??
      ((item as Item).meta?.["format"] as string | undefined));

  const isAudio = isAudioMedia(format);
  const isVideo = ["dvd", "bluray", "video", "moving image"].includes(format?.toLowerCase() || "");
  const isBoardGame = ["boardgame", "board_game", "three-dimensional object"].includes(format?.toLowerCase() || "");
  const isPuzzle = ["puzzle", "jigsaw", "jigsaw puzzle"].includes(format?.toLowerCase() || "");

  const MediaIcon = isAudio ? Disc : isVideo ? Film : isBoardGame ? Dices : isPuzzle ? Puzzle : BookOpen;
  const mediaLabel = isAudio ? "Audio" : isVideo ? "Video" : isBoardGame ? "Board Game" : isPuzzle ? "Puzzle" : "Book";
  const aspectClass = isAudio || isBoardGame || isPuzzle ? "aspect-square" : "aspect-[2/3]";

  const title = item.title ?? "Untitled";
  const authorsList = item.authors ?? [];

  const renderAuthors = () => {
    if (authorsList.length === 0) return <span>Unknown author</span>;
    return (
      <span className="relative z-20">
        {authorsList.map((author, idx) => (
          <span key={author}>
            <button
              type="button"
              onClick={e => {
                e.preventDefault();
                e.stopPropagation();
                router.push(`/collection?q=${encodeURIComponent(author)}`);
              }}
              className="hover:text-primary hover:underline cursor-pointer bg-transparent border-none p-0 font-inherit text-inherit text-left inline"
            >
              {author}
            </button>
            {idx < authorsList.length - 1 ? ", " : ""}
          </span>
        ))}
      </span>
    );
  };

  const quantityBadge = quantity > 1 && (
    <div className="absolute top-2 right-2 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground shadow-md ring-2 ring-background">
      x{quantity}
    </div>
  );

  if (variant === "horizontal") {
    return (
      <Link
        href={targetHref}
        className={`group overflow-hidden rounded-xl bg-card shadow-sm transition-all hover:shadow-md ${!isCatalog && (item as Item).is_hidden ? "opacity-60" : ""}`}
      >
        <div className="flex h-full p-5 gap-4 items-center">
          <div
            className={`relative shrink-0 w-16 sm:w-20 overflow-hidden rounded-md shadow-sm bg-secondary ${aspectClass}`}
          >
            {quantityBadge}
            {(isProcessing || coverStatus === "pending") && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            )}
            {coverUrl ? (
              <Image
                src={coverUrl}
                alt={`Cover of ${title}`}
                fill
                sizes="80px"
                unoptimized
                className={`object-cover transition-transform duration-300 group-hover:scale-105 ${isGenerated ? "sepia-[.15]" : ""}`}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-muted">
                <MediaIcon className="h-6 w-6 text-muted-foreground/30" />
              </div>
            )}
          </div>
          <div className="flex flex-1 flex-col justify-between min-w-0">
            <div>
              <div className="mb-1.5 flex items-center gap-1.5">
                <MediaIcon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground truncate">
                  {mediaLabel}
                </span>
              </div>
              <h3 className="font-serif text-base sm:text-lg font-bold leading-snug text-card-foreground truncate">
                {title}
              </h3>
              <div className="text-xs sm:text-sm text-muted-foreground truncate relative z-10">{renderAuthors()}</div>
              <div className="mt-2.5 flex items-center gap-2">
                {!isCatalog && (
                  <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent whitespace-nowrap">
                    {dotTitle}
                  </span>
                )}
                {isBorrowed && (
                  <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent whitespace-nowrap">
                    Borrowed
                  </span>
                )}
                {isCatalog && userOwns && (
                  <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary whitespace-nowrap">
                    In Collection
                  </span>
                )}
                {!isCatalog && (item as Item).is_hidden && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2.5 py-0.5 text-[10px] font-bold text-zinc-100 ring-1 ring-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-300">
                    <EyeOff className="h-2.5 w-2.5" />
                    HIDDEN
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
    <Link
      href={targetHref}
      className={`group block transition-all ${!isCatalog && (item as Item).is_hidden ? "opacity-60" : ""}`}
    >
      <div className="overflow-hidden rounded-lg bg-card shadow-sm ring-1 ring-border/60 transition-all hover:shadow-md hover:ring-border">
        <div className={`relative w-full overflow-hidden bg-secondary ${aspectClass}`}>
          {quantityBadge}
          {(isProcessing || coverStatus === "pending") && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-background/60 backdrop-blur-sm p-4 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="text-xs font-medium text-foreground">
                {coverStatus === "pending" ? "Generating..." : "Processing..."}
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
              <MediaIcon className="mt-4 h-6 w-6 text-muted-foreground/30" />
            </div>
          )}
        </div>
        <div className="flex items-start gap-2 px-3 py-2.5">
          {!isCatalog && <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotColor}`} title={dotTitle} />}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-snug text-foreground">{title}</p>
            <div className="truncate text-xs text-muted-foreground relative z-10">{renderAuthors()}</div>
            {isCatalog && userOwns && (
              <div className="mt-1.5 flex items-center gap-1 text-[10px] font-medium text-primary">
                <span className="inline-block h-3 w-3 rounded-full bg-primary/20" />
                In Collection
              </div>
            )}
            {isBorrowed && (
              <div className="mt-1 flex items-center gap-1 text-[10px] font-medium text-accent">
                <span className="inline-block h-3 w-3 rounded-full bg-accent/20" />
                Borrowed
              </div>
            )}
            {!isCatalog && (item as Item).is_hidden && (
              <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                <EyeOff className="h-2.5 w-2.5" />
                HIDDEN
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
