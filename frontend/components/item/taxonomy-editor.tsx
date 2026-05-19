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
import { X, Tag } from "lucide-react";
import type { Item } from "@/types/frbr";
import { useUpdateItem } from "@/lib/api/hooks";
import { toast } from "sonner";

interface TaxonomyEditorProps {
  item: Item;
}

/**
 * TaxonomyEditor component for managing item tags
 *
 * @param root0 - The props object
 * @param root0.item - The item to edit taxonomies for
 * @returns {JSX.Element} The component
 */
export function TaxonomyEditor({ item }: TaxonomyEditorProps) {
  const [tagInput, setTagInput] = useState("");
  const updateItem = useUpdateItem(item.id);

  // Initialize tags from item
  const currentTags = item.tags || [];

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (!trimmed) return;
    if (currentTags.includes(trimmed)) {
      setTagInput("");
      return;
    }

    const newTags = [...currentTags, trimmed];
    updateItem.mutate(
      { tags: newTags },
      {
        onSuccess: () => {
          setTagInput("");
          toast.success(`Tag "${trimmed}" added!`);
        },
        onError: err => {
          toast.error(`Failed to add tag: ${(err as Error).message}`);
        },
      }
    );
  };

  const handleRemoveTag = (tagToRemove: string) => {
    const newTags = currentTags.filter(t => t !== tagToRemove);
    updateItem.mutate(
      { tags: newTags },
      {
        onSuccess: () => {
          toast.success(`Tag "${tagToRemove}" removed!`);
        },
        onError: err => {
          toast.error(`Failed to remove tag: ${(err as Error).message}`);
        },
      }
    );
  };

  return (
    <div className="w-full rounded-lg border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Tag className="h-4 w-4 text-muted-foreground" />
        <h3 className="font-serif font-bold text-foreground">Tags</h3>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {currentTags.map(tag => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-500 ring-1 ring-blue-500/20"
          >
            {tag}
            <button
              onClick={() => handleRemoveTag(tag)}
              disabled={updateItem.isPending}
              className="ml-1 rounded-full p-0.5 hover:bg-blue-500/20 disabled:opacity-50"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        {currentTags.length === 0 && <span className="text-xs text-muted-foreground italic">No tags added yet.</span>}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={tagInput}
          onChange={e => setTagInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAddTag();
            }
          }}
          disabled={updateItem.isPending}
          placeholder="Add a new tag..."
          className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          onClick={handleAddTag}
          disabled={updateItem.isPending || !tagInput.trim()}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}
