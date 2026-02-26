"use client";

import { Library } from "lucide-react";
import type { Item } from "@/types/frbr";
import { ItemCard } from "./item-card";

/** Responsive grid of item cards. Shows empty state when no items match. */
export function CollectionGrid({ items }: { items: Item[] }) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Library className="h-7 w-7 text-muted-foreground" />
        </div>
        <h3 className="mt-4 font-serif text-lg font-bold text-foreground">
          No items found
        </h3>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Try adjusting your filters or add some items by scanning a barcode.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((item) => (
        <ItemCard key={item.id} item={item} />
      ))}
    </div>
  );
}
