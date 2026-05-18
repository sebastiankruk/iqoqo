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

import { useMemo, useEffect, useRef } from "react";
import { Library, Loader2 } from "lucide-react";
import type { Item, CatalogEntry } from "@/types/frbr";
import { ItemCard } from "./item-card";

interface CollectionGridProps {
  items: (Item | CatalogEntry)[];
  isManifestationView?: boolean;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onLoadMore?: () => void;
  /** IDs of currently selected manifestations (multi-select mode). */
  selectedIds?: Set<number>;
  /** Toggle selection of a manifestation. */
  onToggleSelect?: (id: number) => void;
}

/**
 * CollectionGrid component renders a responsive grid of items or manifestations
 * with automatic virtual infinite scrolling support.
 *
 * @param props - Component properties.
 * @param props.items - List of items or manifestations to display.
 * @param props.isManifestationView - Flag indicating if grouping should be disabled.
 * @param props.hasMore - Flag indicating if more items can be loaded.
 * @param props.isLoadingMore - Flag indicating if loading is currently in progress.
 * @param props.onLoadMore - Callback to trigger loading more items.
 * @param props.selectedIds - IDs of currently selected manifestations.
 * @param props.onToggleSelect - Callback to toggle selection of a manifestation.
 * @returns Responsive grid component.
 */
export function CollectionGrid({
  items,
  isManifestationView = false,
  hasMore = false,
  isLoadingMore = false,
  onLoadMore,
  selectedIds,
  onToggleSelect,
}: CollectionGridProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore && onLoadMore) {
          onLoadMore();
        }
      },
      { rootMargin: "200px" }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, onLoadMore]);

  const displayItems = useMemo(() => {
    if (isManifestationView) return items;

    const map = new Map<number, (Item | CatalogEntry) & { _quantity?: number }>();
    for (const item of items) {
      const mId = (item as Item).manifestation_id;
      if (mId === undefined) {
        map.set(item.id, { ...item, _quantity: 1 });
        continue;
      }

      if (!map.has(mId)) {
        map.set(mId, { ...item, _quantity: 1 });
      } else {
        const existing = map.get(mId);
        if (existing) {
          existing._quantity = (existing._quantity || 1) + 1;
        }
      }
    }
    return Array.from(map.values()) as (Item | CatalogEntry)[];
  }, [items, isManifestationView]);

  if (displayItems.length === 0 && !isLoadingMore) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Library className="h-7 w-7 text-muted-foreground" />
        </div>
        <h3 className="mt-4 font-serif text-lg font-bold text-foreground">No items found</h3>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Try adjusting your filters or add some items by scanning a barcode.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {displayItems.map(item => (
          <ItemCard
            key={item.id}
            item={item as Item}
            isManifestationView={isManifestationView}
            isSelected={selectedIds?.has(item.id) ?? false}
            onToggleSelect={onToggleSelect}
          />
        ))}
      </div>

      {hasMore && (
        <div ref={loadMoreRef} data-testid="load-more-trigger" className="flex justify-center py-6">
          {isLoadingMore ? <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /> : <div className="h-6" />}
        </div>
      )}
    </div>
  );
}
