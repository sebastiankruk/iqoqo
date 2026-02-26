"use client";

import { useState } from "react";
import { ChevronDown, SlidersHorizontal } from "lucide-react";
import type { ActiveFilter } from "./filter-bar";

interface SidebarFiltersProps {
  activeFilters: ActiveFilter[];
  onToggleFilter: (filter: ActiveFilter) => void;
  statusCounts: Record<string, number>;
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
}: SidebarFiltersProps) {
  return (
    <aside className="w-full">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-serif text-sm font-bold text-foreground">
          Filters
        </h2>
      </div>

      <AccordionSection title="Status">
        <div className="flex flex-col gap-1">
          {statusOptions.map(({ value, label, dot }) => {
            const active = isActive(activeFilters, "status", value);
            return (
              <label
                key={value}
                className={`flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-primary/5 text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => onToggleFilter({ type: "status", value })}
                  className="h-3.5 w-3.5 rounded border-border accent-primary"
                />
                <span className={`h-2 w-2 rounded-full ${dot}`} />
                <span className="flex-1">{label}</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {statusCounts[value] ?? 0}
                </span>
              </label>
            );
          })}
        </div>
      </AccordionSection>
    </aside>
  );
}
