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
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Disc, Dices, Film, HeartOff, Puzzle } from "lucide-react";
import type { WishlistItem } from "@/types/frbr";
import { useDeleteWishlistItem, wishlistQueryKeys } from "@/lib/api/wishlist";
import { resolveMediaBadge } from "@/lib/media-badge";
import { isAudioMedia } from "@/lib/utils";

interface WishlistCardProps {
  item: WishlistItem;
  variant?: "grid" | "horizontal";
}

/**
 * Dedicated card component for rendering wishlist entries.
 * Displays edition and media badges without physical inventory actions
 * (no QR codes, no shelf placement).
 *
 * @param props - WishlistCard component properties
 * @param props.item - Wishlist item data
 * @param props.variant - Layout variant (grid or horizontal)
 * @returns Wishlist card element
 */
export function WishlistCard({ item, variant = "grid" }: WishlistCardProps) {
  const queryClient = useQueryClient();
  const deleteMutation = useDeleteWishlistItem();

  const handleRemove = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteMutation.mutateAsync(item.id);
      queryClient.invalidateQueries({ queryKey: wishlistQueryKeys.all });
      toast.success("Removed from wishlist");
    } catch {
      toast.error("Failed to remove from wishlist");
    }
  };

  const coverUrl = item.cover_url;
  const title = item.title || "Untitled";
  const authors = item.authors || [];
  const targetHref = item.manifestation_id ? `/manifestation/${item.manifestation_id}` : "/wishlist";

  const rawContentType = item.content_type ?? item.expression?.content_type;
  const format =
    (item.manifestation_meta?.["format"] as string | undefined) ??
    (item.manifestation_meta?.["Format"] as string | undefined) ??
    item.medium_type;

  const badge = resolveMediaBadge({
    content_type: rawContentType,
    kind: item.expression?.kind,
    format,
    work_type: item.work_type,
    medium_type: item.medium_type,
  });

  const isAudio = badge.isAudio || isAudioMedia(format ?? undefined) || isAudioMedia(rawContentType ?? undefined);
  const isVideo =
    badge.typeKey === "movie" ||
    ["dvd", "bluray", "video", "moving image"].includes((format || rawContentType || "").toLowerCase());
  const isBoardGame =
    badge.typeKey === "game" ||
    ["boardgame", "board_game", "three-dimensional object"].includes((format || rawContentType || "").toLowerCase());
  const isPuzzle =
    rawContentType === "puzzle" ||
    format?.toLowerCase() === "puzzle" ||
    ["puzzle", "jigsaw", "jigsaw puzzle"].includes((format || "").toLowerCase());

  const MediaIcon = isAudio
    ? Disc
    : isVideo
      ? Film
      : isBoardGame
        ? isPuzzle
          ? Puzzle
          : Dices
        : isPuzzle
          ? Puzzle
          : BookOpen;

  const aspectClass = isAudio || isBoardGame || isPuzzle ? "aspect-square" : "aspect-[2/3]";
  const mediaLabel = item.content_type ?? item.expression?.content_type ?? item.medium_type;

  if (variant === "horizontal") {
    return (
      <Link
        href={targetHref}
        data-testid="item-card"
        className="group flex min-h-40 gap-4 overflow-hidden rounded-xl bg-card p-5 shadow-sm transition-all hover:shadow-md"
      >
        <div
          className={`relative ${aspectClass} w-16 shrink-0 overflow-hidden rounded-md bg-secondary shadow-sm sm:w-20`}
        >
          {coverUrl ? (
            <img src={coverUrl} alt={title} className="h-full w-full object-cover" loading="lazy" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <MediaIcon className="h-6 w-6 text-muted-foreground/40" />
            </div>
          )}
        </div>
        <div className="min-w-0 self-center">
          <h3 data-testid="card-title" className="line-clamp-2 font-serif text-base font-bold text-foreground">
            {title}
          </h3>
          {authors.length > 0 && (
            <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">{authors.join(", ")}</p>
          )}
          {mediaLabel && (
            <span className="mt-3 inline-block rounded bg-primary/10 px-2 py-1 text-xs text-muted-foreground">
              {mediaLabel}
            </span>
          )}
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={targetHref}
      data-testid="item-card"
      className="group relative block overflow-hidden rounded-lg border bg-card text-card-foreground shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Cover image */}
      <div className={`relative ${aspectClass} overflow-hidden bg-muted`}>
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={title}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 p-4 text-center text-muted-foreground">
            <MediaIcon className="h-8 w-8 text-muted-foreground/40" />
            <span className="line-clamp-2 text-xs font-medium text-muted-foreground/60">{title}</span>
          </div>
        )}
      </div>

      {/* Remove button */}
      <button
        type="button"
        aria-label="Remove from wishlist"
        onClick={handleRemove}
        className="absolute top-2 right-2 z-20 flex h-7 w-7 items-center justify-center rounded-full bg-background/80 text-destructive opacity-0 group-hover:opacity-100 transition-opacity shadow-sm ring-1 ring-border hover:bg-destructive hover:text-destructive-foreground"
      >
        <HeartOff className="h-3.5 w-3.5" />
      </button>

      {/* Content type badge */}
      {item.content_type && (
        <span className="absolute top-2 left-2 z-10 rounded bg-primary/90 px-1.5 py-0.5 text-[10px] font-medium text-primary-foreground">
          {item.content_type}
        </span>
      )}

      {/* Info */}
      <div className="p-3">
        <h3 data-testid="card-title" className="line-clamp-2 text-sm font-medium leading-tight">
          {title}
        </h3>
        {authors.length > 0 && <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{authors.join(", ")}</p>}
        {mediaLabel && (
          <span className="mt-2 inline-block rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {mediaLabel}
          </span>
        )}
      </div>
    </Link>
  );
}
