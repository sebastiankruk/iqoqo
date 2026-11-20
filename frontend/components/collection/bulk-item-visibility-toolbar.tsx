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

import { useEffect, useRef, useState } from "react";
import { Eye, EyeOff, Users, X, Loader2, ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

type TargetVisibility = "public" | "friends_only" | "private";

interface BulkItemVisibilityToolbarProps {
  /** IDs of currently selected physical items owned by the user. */
  selectedItemIds: number[];
  /** Clear all selected items. */
  onClearSelection: () => void;
  /** Callback invoked after bulk visibility mutation succeeds. */
  onSuccess?: () => void;
}

/**
 * Floating action bar for bulk-updating visibility across selected owned physical items.
 *
 * @param props - Component properties.
 * @returns Floating toolbar element or null when nothing is selected.
 */
export function BulkItemVisibilityToolbar({
  selectedItemIds,
  onClearSelection,
  onSuccess,
}: BulkItemVisibilityToolbarProps) {
  const t = useTranslations("CollectionFilters");
  const queryClient = useQueryClient();
  const [isUpdating, setIsUpdating] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const menuContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dropdownOpen) return;

    const handleOutsideMouseDown = (event: MouseEvent) => {
      if (menuContainerRef.current && !menuContainerRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideMouseDown);
    document.addEventListener("keydown", handleEscapeKey);
    return () => {
      document.removeEventListener("mousedown", handleOutsideMouseDown);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [dropdownOpen]);

  if (selectedItemIds.length === 0) return null;

  const options: Array<{ value: TargetVisibility; label: string; Icon: typeof Eye }> = [
    { value: "public", label: t("visibilityPublic"), Icon: Eye },
    { value: "friends_only", label: t("visibilityFriendsOnly"), Icon: Users },
    { value: "private", label: t("visibilityPrivate"), Icon: EyeOff },
  ];

  const handleApply = async (visibility: TargetVisibility) => {
    setDropdownOpen(false);
    setIsUpdating(true);
    try {
      await apiClient.patch("/items/bulk-visibility", {
        item_ids: selectedItemIds,
        visibility,
      });
      toast.success(t("bulkVisibilitySuccess", { count: selectedItemIds.length }));
      queryClient.invalidateQueries({ queryKey: ["items"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["facetStats"] });
      onSuccess?.();
    } catch {
      toast.error(t("bulkVisibilityError"));
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div
      data-testid="bulk-item-visibility-toolbar"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-2xl border border-border bg-card/95 backdrop-blur-md px-4 py-2.5 shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-200 max-w-[95vw]"
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground whitespace-nowrap">
        <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-primary px-2 text-xs font-bold text-primary-foreground">
          {selectedItemIds.length}
        </span>
        <span>{t("bulkVisibilitySelected", { count: selectedItemIds.length })}</span>
      </div>

      <div className="h-5 w-px bg-border" />

      <div className="relative" ref={menuContainerRef}>
        <button
          type="button"
          disabled={isUpdating}
          onClick={() => setDropdownOpen(prev => !prev)}
          data-testid="bulk-visibility-trigger"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-60 transition-colors cursor-pointer whitespace-nowrap"
        >
          {isUpdating ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>{t("bulkVisibilityUpdating")}</span>
            </>
          ) : (
            <>
              <Eye className="h-3.5 w-3.5" />
              <span>{t("bulkVisibilityLabel")}</span>
              <ChevronDown className="h-3.5 w-3.5" />
            </>
          )}
        </button>

        {dropdownOpen && !isUpdating && (
          <div
            role="menu"
            data-testid="bulk-visibility-menu"
            className="absolute bottom-full mb-2 left-0 w-56 rounded-xl border border-border bg-card p-1 shadow-xl z-50"
          >
            {options.map(({ value, label, Icon }) => (
              <button
                key={value}
                type="button"
                role="menuitem"
                onClick={() => handleApply(value)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-foreground hover:bg-accent/10 hover:text-accent transition-colors cursor-pointer"
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        type="button"
        disabled={isUpdating}
        onClick={onClearSelection}
        aria-label={t("bulkVisibilityClear")}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
      >
        <X className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">{t("bulkVisibilityClear")}</span>
      </button>
    </div>
  );
}
