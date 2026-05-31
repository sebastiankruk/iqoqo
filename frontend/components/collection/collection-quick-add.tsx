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

import React, { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

interface CollectionQuickAddProps {
  onCollectionCreated?: (collectionId: number) => void;
}

/**
 * A lightweight inline input to instantly create a new Collection folder.
 * Best nested at the bottom of standard "Add to Collection" dropdowns.
 *
 * @param root0 - Component props
 * @param root0.onCollectionCreated - Callback when a collection is created
 * @returns {JSX.Element} The component
 */
export function CollectionQuickAdd({ onCollectionCreated }: CollectionQuickAddProps) {
  const [name, setName] = useState("");
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: async (collectionName: string) => {
      const res = await apiClient.post("/collections", { name: collectionName });
      return res.data;
    },
    onSuccess: response => {
      // Invalidate collections list so taxonomies refresh globally
      queryClient.invalidateQueries({ queryKey: ["user-collections"] });
      // Also invalidate taxonomies query if it exists
      queryClient.invalidateQueries({ queryKey: ["taxonomies"] });

      setName("");
      if (onCollectionCreated && response.collection) {
        onCollectionCreated(response.collection.id);
      }
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      createMutation.mutate(name.trim());
    }
  };

  return (
    <form onSubmit={handleCreate} className="flex items-center gap-2 p-2 border-t border-border bg-muted/30">
      <input
        type="text"
        placeholder="New collection..."
        value={name}
        onChange={e => setName(e.target.value)}
        className="flex h-8 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        disabled={createMutation.isPending}
      />
      <button
        type="submit"
        disabled={!name.trim() || createMutation.isPending}
        className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      </button>
    </form>
  );
}
