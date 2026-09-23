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
import type { WishlistItem } from "@/types/frbr";
import { useDeleteWishlistItem, wishlistQueryKeys } from "@/lib/api/wishlist";

interface WishlistCardProps {
  item: WishlistItem;
  variant?: "grid" | "horizontal";
}

/**
 * Dedicated card component for rendering wishlist entries.
 * Displays edition and media badges without physical inventory actions
 * (no QR codes, no shelf placement).
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
  const mediaLabel = item.content_type ?? item.expression?.content_type ?? item.medium_type;
  const targetHref = item.manifestation_id ? `/manifestation/${item.manifestation_id}` : "/wishlist";

  if (variant === "horizontal") {
    return (
      <Link
        href={targetHref}
        className="group flex min-h-40 gap-4 overflow-hidden rounded-xl bg-card p-5 shadow-sm transition-all hover:shadow-md"
      >
        <div className="relative aspect-[2/3] w-16 shrink-0 overflow-hidden rounded-md bg-secondary shadow-sm sm:w-20">
          {coverUrl ? (
            <img src={coverUrl} alt={title} className="h-full w-full object-cover" loading="lazy" />
          ) : (
            <div className="flex h-full items-center justify-center text-2xl">📖</div>
          )}
        </div>
        <div className="min-w-0 self-center">
          <h3 className="line-clamp-2 font-serif text-base font-bold text-foreground">{title}</h3>
          {authors.length > 0 && (
            <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">{authors.join(", ")}</p>
          )}
          {mediaLabel && <span className="mt-3 inline-block rounded bg-primary/10 px-2 py-1 text-xs text-muted-foreground">{mediaLabel}</span>}
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={targetHref}
      className="group relative block overflow-hidden rounded-lg border bg-card text-card-foreground shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Cover image */}
      <div className="aspect-[2/3] overflow-hidden bg-muted">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={title}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <span className="text-4xl">📖</span>
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
        ✕
      </button>

      {/* Content type badge */}
      {item.content_type && (
        <span className="absolute top-2 left-2 z-10 rounded bg-primary/90 px-1.5 py-0.5 text-[10px] font-medium text-primary-foreground">
          {item.content_type}
        </span>
      )}

      {/* Info */}
      <div className="p-3">
        <h3 className="line-clamp-2 text-sm font-medium leading-tight">
          {title}
        </h3>
        {authors.length > 0 && (
          <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
            {authors.join(", ")}
          </p>
        )}
        {mediaLabel && <span className="mt-2 inline-block rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{mediaLabel}</span>}
      </div>
    </Link>
  );
}
