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
import { ChevronDown, SlidersHorizontal } from "lucide-react";
import type { ActiveFilter } from "./filter-bar";

interface SidebarFiltersProps {
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts: Record<string, number>;
  disableStatus?: boolean; // Fixed missing prop
}

const statusOptions: { value: string; label: string; dot: string }[] = [
  { value: "available", label: "On Shelf", dot: "bg-chart-3" },
  { value: "reading", label: "Reading", dot: "bg-green-500" },
  { value: "wish_list", label: "On Wish List", dot: "bg-primary" },
  { value: "lent", label: "Lent Out", dot: "bg-accent" },
  { value: "lost", label: "Lost", dot: "bg-destructive" },
  { value: "read", label: "Read", dot: "bg-blue-500" },
];

function isActive(filters: ActiveFilter[], type: string, value: string) {
  return filters.some((f) => f.type === type && f.value === value);
}

function AccordionSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-border pb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
      >
        {title}
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${open ? "" : "-rotate-90"}`}
        />
      </button>
      <div
        className={`overflow-hidden transition-all ${
          open ? "max-h-96 pb-3 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

/** Desktop sidebar with collapsible filter sections. */
export function SidebarFilters({
  activeFilters,
  onToggleFilter,
  statusCounts,
  disableStatus,
}: SidebarFiltersProps) {
  return (
    <aside className="w-full">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-serif text-sm font-bold text-foreground">Filters</h2>
      </div>

      <AccordionSection title="Status">
        {disableStatus ? (
          <p className="px-2 py-1.5 text-xs text-muted-foreground">Not applicable in Global Library view.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {statusOptions.map(({ value, label, dot }) => {
              const active = isActive(activeFilters, "status", value);
              return (
                <label key={value} className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${active ? "bg-primary/5 text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                  <input type="checkbox" checked={active} onChange={() => onToggleFilter({ type: "status", value })} className="h-3.5 w-3.5 rounded border-border accent-primary" />
                  <span className={`h-2 w-2 rounded-full ${dot}`} />
                  <span className="flex-1">{label}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{statusCounts[value] ?? 0}</span>
                </label>
              );
            })}
          </div>
        )}
      </AccordionSection>
    </aside>
  );
}
