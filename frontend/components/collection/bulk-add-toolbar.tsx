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

import { useState, useMemo } from "react";
import { PlusCircle, X, ChevronDown, Loader2, CheckCheck } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@/types/frbr";

/* ── Category → progress status mapping ───────────────────────────────────── */

/**
 * For each content_type category returns the relevant [want, done] progress
 * status pair. Matches `CATEGORY_PROGRESS_STATUSES` in the backend taxonomy.
 */
const CATEGORY_STATUSES: Record<string, { want: string; done: string }> = {
  text: { want: "want_to_read", done: "read" },
  audiobook: { want: "want_to_listen", done: "listened" },
  music: { want: "want_to_listen", done: "listened" },
  movie: { want: "want_to_watch", done: "watched" },
  board_game: { want: "want_to_play", done: "played" },
  puzzle: { want: "want_to_play", done: "played" },
};

/** Human-readable label fragments per category for the "want" action. */
const WANT_LABEL: Record<string, string> = {
  text: "Read",
  audiobook: "Listen",
  music: "Listen",
  movie: "Watch",
  board_game: "Play",
  puzzle: "Play",
};

/** Human-readable label fragments per category for the "done" action. */
const DONE_LABEL: Record<string, string> = {
  text: "Read",
  audiobook: "Listened",
  music: "Listened",
  movie: "Watched",
  board_game: "Played",
  puzzle: "Played",
};

interface StatusOption {
  /** User-visible label. */
  label: string;
  /** `status` API field value. */
  value: string;
  /** `collection_status` API field value. */
  collectionStatus: string;
}

/**
 * Derives context-aware status options from the set of selected manifestations.
 * When multiple media categories are present the labels are merged, e.g.
 * "Want to Read / Listen" for text + music items.
 *
 * @param items - The selected catalog entries.
 * @returns An ordered list of status options to offer the user.
 */
function deriveStatusOptions(items: CatalogEntry[]): StatusOption[] {
  // Collect the unique categories present in the selection
  const categories = new Set<string>();
  for (const item of items) {
    const cat = (item.content_type ?? "text").toLowerCase();
    categories.add(CATEGORY_STATUSES[cat] ? cat : "text");
  }

  if (categories.size === 0) {
    categories.add("text");
  }

  // Build combined "want" label (e.g. "Read / Listen / Watch")
  const wantVerbs = [...new Set([...categories].map(c => WANT_LABEL[c] ?? "Read"))];
  const doneVerbs = [...new Set([...categories].map(c => DONE_LABEL[c] ?? "Read"))];

  // Dominant "want" status: use the first category's status value (best effort)
  const firstCat = [...categories][0];
  const wantStatus = CATEGORY_STATUSES[firstCat]?.want ?? "want_to_read";
  const doneStatus = CATEGORY_STATUSES[firstCat]?.done ?? "read";

  const options: StatusOption[] = [
    {
      label: `Want to ${wantVerbs.join(" / ")}`,
      value: wantStatus,
      collectionStatus: "wish_list",
    },
    {
      label: "Ordered",
      value: wantStatus,
      collectionStatus: "ordered",
    },
    {
      label: doneVerbs.join(" / "),
      value: doneStatus,
      collectionStatus: "available",
    },
    {
      label: "On shelf (no status)",
      value: wantStatus,
      collectionStatus: "available",
    },
  ];

  return options;
}

interface BulkAddToolbarProps {
  /** Selected CatalogEntry items (used to derive smart status options). */
  selectedItems: CatalogEntry[];
  /** Clears the selection. */
  onClearSelection: () => void;
  /** Called after a successful bulk-add so the parent can refresh. */
  onSuccess: () => void;
}

/**
 * Floating action toolbar that appears when manifestations are selected in
 * the Global Library view. Derives context-aware status options from the
 * content types of selected items and bulk-adds them in one API request.
 *
 * @param props - Component props.
 * @param props.selectedItems - The selected catalog entries.
 * @param props.onClearSelection - Callback to reset the selection.
 * @param props.onSuccess - Callback invoked on successful bulk-add.
 * @returns The toolbar element, or null when nothing is selected.
 */
export function BulkAddToolbar({ selectedItems, onClearSelection, onSuccess }: BulkAddToolbarProps) {
  const qc = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  const statusOptions = useMemo(() => deriveStatusOptions(selectedItems), [selectedItems]);

  if (selectedItems.length === 0) return null;

  /**
   * Sends a bulk-add request for the given status option.
   *
   * @param option - The chosen status / collection-status pair.
   * @returns Promise that resolves after the request completes.
   */
  const handleAdd = async (option: StatusOption) => {
    setIsOpen(false);
    setIsAdding(true);
    try {
      await apiClient.post("/items/bulk", {
        manifestation_ids: selectedItems.map(i => i.id),
        status: option.value,
        collection_status: option.collectionStatus,
      });
      toast.success(
        `Added ${selectedItems.length} item${selectedItems.length > 1 ? "s" : ""} as "${option.label}" to your collection.`
      );
      // Invalidate caches so My Items and stats refresh
      await qc.invalidateQueries({ queryKey: ["items"] });
      await qc.invalidateQueries({ queryKey: ["manifestations"] });
      await qc.invalidateQueries({ queryKey: ["stats"] });
      onClearSelection();
      onSuccess();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to add items";
      toast.error(msg);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div
      role="toolbar"
      aria-label="Bulk add selected manifestations"
      className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-2xl ring-1 ring-primary/20 animate-in fade-in slide-in-from-bottom-4 duration-200"
    >
      {/* Selection count */}
      <span className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <CheckCheck className="h-4 w-4 text-primary" />
        {selectedItems.length} selected
      </span>

      <span className="h-5 w-px bg-border" aria-hidden />

      {/* Status picker dropdown */}
      <div className="relative">
        <button
          id="bulk-add-status-button"
          onClick={() => setIsOpen(prev => !prev)}
          disabled={isAdding}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          {isAdding ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Adding…
            </>
          ) : (
            <>
              <PlusCircle className="h-3.5 w-3.5" />
              Add to Collection as…
              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </>
          )}
        </button>

        {isOpen && (
          <ul
            role="listbox"
            aria-label="Select status to add items as"
            className="absolute bottom-full mb-2 left-0 min-w-52 rounded-xl border border-border bg-card shadow-xl overflow-hidden"
          >
            {statusOptions.map(opt => (
              <li key={`${opt.value}-${opt.collectionStatus}`}>
                <button
                  role="option"
                  aria-selected={false}
                  onClick={() => handleAdd(opt)}
                  className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-secondary transition-colors"
                >
                  {opt.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Dismiss */}
      <button
        aria-label="Clear selection"
        onClick={onClearSelection}
        className="rounded-full p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
