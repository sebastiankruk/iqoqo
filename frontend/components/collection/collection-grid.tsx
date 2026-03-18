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

import { Library } from "lucide-react";
import type { Item, CatalogEntry } from "@/types/frbr";
import { ItemCard } from "./item-card";

/**
 * Responsive grid of item cards. Shows empty state when no items match.
 *
 * @param root0 - The props object
 * @param root0.items - The items to display
 * @param root0.isManifestationView - Whether to show the manifestation view
 * @returns {JSX.Element} The component
 */
export function CollectionGrid({ items, isManifestationView = false }: { items: (Item | CatalogEntry)[]; isManifestationView?: boolean }) {
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
        <ItemCard key={item.id} item={item as Item} isManifestationView={isManifestationView} />
      ))}
    </div>
  );
}
