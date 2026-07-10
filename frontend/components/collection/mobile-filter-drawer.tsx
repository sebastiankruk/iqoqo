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

import { useEffect } from "react";
import { X, SlidersHorizontal } from "lucide-react";
import type { ActiveFilter } from "./filter-bar";
import { SidebarFilters } from "./sidebar-filters";
import { useTranslations } from "next-intl";

/** Props for MobileFilterDrawer component */
interface MobileFilterDrawerProps {
  open: boolean;
  onClose: () => void;
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts: Record<string, number>;
  formatCounts?: Record<string, number>;
  categoryCounts?: Record<string, number>;
  disableStatus?: boolean;
  viewMode?: "items" | "manifestations" | "works" | "expressions" | "roadmap";
  isLoggedIn?: boolean;
  isCurator?: boolean;
  missingCover?: boolean;
  onChangeMissingCover?: (checked: boolean) => void;
  missingId?: boolean;
  onChangeMissingId?: (checked: boolean) => void;
}

/**
 * Slide-in drawer for filter controls on mobile devices.
 *
 * @param root0 - The props object
 * @param root0.open - Whether the drawer is open
 * @param root0.onClose - Callback to close the drawer
 * @param root0.activeFilters - The active filters
 * @param root0.onToggleFilter - Callback to toggle a filter
 * @param root0.statusCounts - The counts for each status
 * @param root0.formatCounts - The counts for each format
 * @param root0.categoryCounts - The counts for each category
 * @param root0.disableStatus - Whether to disable the status filter
 * @param root0.viewMode - The current view mode
 * @param root0.isLoggedIn - Whether the user is logged in
 * @param root0.isCurator - Whether the user is a curator
 * @param root0.missingCover - Filter for items with missing cover
 * @param root0.onChangeMissingCover - Change handler for missing cover filter
 * @param root0.missingId - Filter for items with missing ID
 * @param root0.onChangeMissingId - Change handler for missing ID filter
 * @returns {JSX.Element} The component*/
export function MobileFilterDrawer({
  open,
  onClose,
  activeFilters,
  onToggleFilter,
  statusCounts,
  formatCounts,
  categoryCounts = {},
  disableStatus = false,
  viewMode = "items",
  isLoggedIn = false,
  isCurator = false,
  missingCover = false,
  onChangeMissingCover,
  onChangeMissingId,
  missingId = false,
}: MobileFilterDrawerProps) {
  const t = useTranslations("CollectionFilters");
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-foreground/30 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-card shadow-xl transition-transform lg:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label={t("filterDrawer")}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
              <span className="font-serif text-sm font-bold text-foreground">{t("title")}</span>
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
              aria-label={t("closeFilters")}
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            <SidebarFilters
              activeFilters={activeFilters}
              onToggleFilter={onToggleFilter}
              statusCounts={statusCounts}
              formatCounts={formatCounts}
              categoryCounts={categoryCounts}
              disableStatus={disableStatus}
              viewMode={viewMode}
              isLoggedIn={isLoggedIn}
              isCurator={isCurator}
              missingCover={missingCover}
              onChangeMissingCover={onChangeMissingCover}
              missingId={missingId}
              onChangeMissingId={onChangeMissingId}
            />
          </div>

          <div className="border-t border-border p-4">
            <button
              onClick={onClose}
              className="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              {t("showResults")}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
