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

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import Link from "next/link";
import { ItemEditor } from "./item-editor";
import type { ItemFormData } from "./types";
import type { FrbrItem } from "@/lib/api/admin";

/**
 * Props for the ItemsManager component.
 */
interface ItemsManagerProps {
  items: FrbrItem[];
  onItemSubmit: (data: ItemFormData, itemId: number) => Promise<void>;
  onItemEscalate?: (itemId: number) => void;
  onItemDelete?: (itemId: number) => void;
  lastFetched: number;
}

/**
 * Manages the list of items with filtering, expansion, and multi-item editing.
 * Supports owner, status, and condition filters.
 *
 * @param props - Component properties
 * @param props.items - The list of FRBR items
 * @param props.onItemSubmit - Handler for item form submission
 * @param props.onItemEscalate - Optional handler for escalating an item
 * @param props.onItemDelete - Optional handler for deleting an item
 * @param props.lastFetched - Timestamp for key-based re-rendering
 * @returns JSX element
 */
export function ItemsManager({ items, onItemSubmit, onItemEscalate, onItemDelete, lastFetched }: ItemsManagerProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const [itemFilter, setItemFilter] = useState({ owner: "", status: "", condition: "" });

  const toggleItemExpanded = (itemId: number) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const filteredItems = items.filter(item => {
    if (
      itemFilter.owner &&
      !(
        item.owner_name?.toLowerCase().includes(itemFilter.owner.toLowerCase()) ||
        item.owner_id.toLowerCase().includes(itemFilter.owner.toLowerCase())
      )
    ) {
      return false;
    }
    if (itemFilter.status && item.status.toLowerCase() !== itemFilter.status.toLowerCase()) {
      return false;
    }
    if (
      itemFilter.condition &&
      !(item.condition?.toLowerCase().includes(itemFilter.condition.toLowerCase()) ?? false)
    ) {
      return false;
    }
    return true;
  });

  if (items.length === 0) {
    return <p className="text-muted-foreground">No items associated with this manifestation.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground mb-1 block">Owner</label>
          <input
            placeholder="Filter by owner name or email"
            value={itemFilter.owner}
            onChange={e => setItemFilter(prev => ({ ...prev, owner: e.target.value }))}
            data-testid="filter-owner"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
        <div className="w-40">
          <label className="text-xs text-muted-foreground mb-1 block">Status</label>
          <select
            value={itemFilter.status}
            onChange={e => setItemFilter(prev => ({ ...prev, status: e.target.value }))}
            data-testid="filter-status"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="">All</option>
            <option value="available">available</option>
            <option value="lent">lent</option>
            <option value="lost">lost</option>
            <option value="wish_list">wish_list</option>
          </select>
        </div>
        <div className="w-40">
          <label className="text-xs text-muted-foreground mb-1 block">Condition</label>
          <input
            placeholder="Filter by condition"
            value={itemFilter.condition}
            onChange={e => setItemFilter(prev => ({ ...prev, condition: e.target.value }))}
            data-testid="filter-condition"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>
      <div className="border rounded-lg divide-y">
        {filteredItems.map(item => (
          <div key={item.id}>
            <button
              type="button"
              className="w-full flex items-center justify-between p-4 hover:bg-muted/50 text-left"
              onClick={() => toggleItemExpanded(item.id)}
            >
              <div className="flex items-center gap-3">
                {expandedItems.has(item.id) ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
                <div>
                  <span className="font-medium">
                    <Link
                      href={`/item/${item.id}`}
                      className="hover:underline hover:text-primary transition-colors"
                      target="_blank"
                      onClick={e => e.stopPropagation()}
                    >
                      Item #{item.id}
                    </Link>
                  </span>
                  <span className="text-sm text-muted-foreground ml-2">
                    {item.status} {item.condition && `• ${item.condition}`}
                  </span>
                </div>
              </div>
              <span
                className="text-sm text-muted-foreground truncate max-w-[200px]"
                title={item.owner_name || item.owner_id}
              >
                {item.owner_name || item.owner_id}
              </span>
            </button>
            {expandedItems.has(item.id) && (
              <div className="p-4 pt-0 border-t bg-muted/20">
                <ItemEditor
                  key={`${item.id}-${lastFetched}`}
                  item={item}
                  onSubmit={data => onItemSubmit(data, item.id)}
                  onEscalate={onItemEscalate ? () => onItemEscalate(item.id) : undefined}
                  onDelete={onItemDelete ? () => onItemDelete(item.id) : undefined}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
