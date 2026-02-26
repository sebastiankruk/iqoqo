"use client";

import { useEffect } from "react";
import { X, SlidersHorizontal } from "lucide-react";
import type { ActiveFilter } from "./filter-bar";
import { SidebarFilters } from "./sidebar-filters";

interface MobileFilterDrawerProps {
  open: boolean;
  onClose: () => void;
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts: Record<string, number>;
}

/** Slide-in drawer for filter controls on mobile devices. */
export function MobileFilterDrawer({
  open,
  onClose,
  activeFilters,
  onToggleFilter,
  statusCounts,
}: MobileFilterDrawerProps) {
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
        aria-label="Filter drawer"
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
              <span className="font-serif text-sm font-bold text-foreground">
                Filters
              </span>
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close filters"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            <SidebarFilters
              activeFilters={activeFilters}
              onToggleFilter={onToggleFilter}
              statusCounts={statusCounts}
            />
          </div>

          <div className="border-t border-border p-4">
            <button
              onClick={onClose}
              className="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              Show Results
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
