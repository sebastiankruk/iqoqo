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

import React, { useState, useRef, useEffect } from "react";
import { BookOpen, ChevronDown, Library, Loader2, BookmarkPlus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { useUserCollections } from "@/lib/api/hooks";
import { CollectionQuickAdd } from "./collection-quick-add";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

interface AddToCollectionDropdownProps {
  manifestationId: number;
  wishlistItemId?: number | null;
}

/**
 * Dropdown button that lets the user add a manifestation to one of their collections.
 * The top option always adds to the user's general library (no named collection folder).
 *
 * @param root0 - Component props
 * @param root0.manifestationId - The ID of the manifestation to add
 * @returns React node representing the dropdown component
 */
export function AddToCollectionDropdown({ manifestationId, wishlistItemId }: AddToCollectionDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();
  const router = useRouter();
  const { data: collections, isLoading: collectionsLoading } = useUserCollections();

  useEffect(() => {
    /**
     * Closes the dropdown when clicking outside its bounds.
     *
     * @param event - Mouse click event
     */
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const addMutation = useMutation({
    mutationFn: async ({
      collectionId,
      collectionStatus,
    }: {
      collectionId: number | null;
      collectionStatus?: string;
    }) => {
      const payload: Record<string, unknown> = {};
      if (collectionId !== null) {
        payload.collection_id = collectionId;
      }
      if (collectionStatus) {
        payload.collection_status = collectionStatus;
      }
      const res = await apiClient.post(`/manifestations/${manifestationId}/add`, payload);
      return res.data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["items"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["manifestations"] });
      qc.invalidateQueries({ queryKey: ["worksShelf"] });
      qc.invalidateQueries({ queryKey: ["expressionsShelf"] });
      if (variables.collectionStatus === "wish_list") {
        toast.success("Added to your wishlist!");
      } else {
        toast.success("Added to your collection!");
      }
      setIsOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message ?? "Failed to add to collection");
    },
  });

  const handleCollectionClick = (collectionId: number) => {
    addMutation.mutate({ collectionId });
  };

  const handleQuickAdd = (collectionId: number) => {
    qc.invalidateQueries({ queryKey: ["collections"] });
    qc.invalidateQueries({ queryKey: ["user-collections"] });
    addMutation.mutate({ collectionId });
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(prev => !prev)}
        disabled={addMutation.isPending}
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:opacity-60"
      >
        {addMutation.isPending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <BookOpen className="mr-2 h-4 w-4" />
        )}
        Add to Collection
        <ChevronDown className={`ml-2 h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-2 min-w-56 rounded-xl border border-border bg-card shadow-xl overflow-hidden z-50">
          {/* Wishlist option */}
          <div className="border-b border-border/50">
            {wishlistItemId ? (
              <button
                onClick={() => router.push(`/item/${wishlistItemId}`)}
                className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-foreground hover:bg-primary/5 hover:text-primary transition-colors"
              >
                <BookmarkPlus className="h-4 w-4 shrink-0 text-primary" />
                <span>View Wishlist Item</span>
              </button>
            ) : (
              <button
                onClick={() => addMutation.mutate({ collectionId: null, collectionStatus: "wish_list" })}
                disabled={addMutation.isPending}
                className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-foreground hover:bg-primary/5 hover:text-primary transition-colors"
              >
                <BookmarkPlus className="h-4 w-4 shrink-0 text-primary" />
                <span>Add to Wishlist</span>
              </button>
            )}
          </div>

          {/* Primary option: add to general library without any named folder */}
          <div className="border-b border-border/50">
            <button
              onClick={() => addMutation.mutate({ collectionId: null })}
              disabled={addMutation.isPending}
              className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-foreground hover:bg-primary/5 hover:text-primary transition-colors"
            >
              <Library className="h-4 w-4 shrink-0 text-primary" />
              <span>Add to My Library</span>
              <span className="ml-auto text-[10px] text-muted-foreground font-normal">No folder</span>
            </button>
          </div>

          {collectionsLoading ? (
            <div className="flex items-center justify-center px-4 py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : collections && collections.length > 0 ? (
            <ul className="max-h-60 overflow-y-auto py-1">
              {collections.map(collection => (
                <li key={collection.id}>
                  <button
                    onClick={() => handleCollectionClick(collection.id)}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-secondary transition-colors"
                  >
                    <span className="flex-1 truncate">{collection.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-4 py-3 text-center text-xs text-muted-foreground">
              No named folders yet. Create one below.
            </div>
          )}

          <CollectionQuickAdd onCollectionCreated={handleQuickAdd} />
        </div>
      )}
    </div>
  );
}
