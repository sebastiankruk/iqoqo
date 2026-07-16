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
import { SlidersHorizontal } from "lucide-react";
import type { ActiveFilter } from "./filter-bar";
import { SidebarFilters } from "./sidebar-filters";
import { useTranslations } from "next-intl";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerFooter, DrawerClose } from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";

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
  tagCounts?: Record<string, number>;
  collectionCounts?: Record<string, number>;
  genreCounts?: Record<string, number>;
  publisherCounts?: Record<string, number>;
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
 * @param root0.tagCounts - The counts for tags
 * @param root0.collectionCounts - The counts for collections
 * @param root0.genreCounts - The counts for genres
 * @param root0.publisherCounts - The counts for publishers
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
  tagCounts = {},
  collectionCounts: collCounts = {},
  genreCounts = {},
  publisherCounts = {},
}: MobileFilterDrawerProps) {
  const t = useTranslations("CollectionFilters");
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <Drawer open={open} onOpenChange={isOpen => !isOpen && onClose()}>
      <DrawerContent className="h-[85vh] lg:hidden">
        <DrawerHeader className="border-b border-border text-left px-5 py-4 flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
          <DrawerTitle className="font-serif text-sm font-bold text-foreground">{t("title")}</DrawerTitle>
        </DrawerHeader>

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
            tagCounts={tagCounts}
            collectionCounts={collCounts}
            genreCounts={genreCounts}
            publisherCounts={publisherCounts}
          />
        </div>

        <DrawerFooter className="border-t border-border p-4 pt-4">
          <DrawerClose asChild>
            <Button className="w-full font-semibold">{t("showResults")}</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
