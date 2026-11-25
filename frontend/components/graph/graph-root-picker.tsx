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

import React, { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { useCatalogGraphSearch } from "@/lib/api/hooks/catalog";
import type { GraphAnchorEntityType, GraphRootSearchResult } from "@/types/frbr";

export interface GraphRootPickerProps {
  onSelect: (entityType: GraphAnchorEntityType, entityId: number) => void;
  defaultTypeFilter?: string;
}

const PICKER_TYPES = ["all", "person", "series", "work", "expression", "manifestation", "item"] as const;

/**
 * Keyboard-accessible ARIA combobox for searching and selecting any FRBR or Contributor graph root.
 */
export function GraphRootPicker({ onSelect, defaultTypeFilter = "all" }: GraphRootPickerProps) {
  const t = useTranslations("graph");
  const listboxId = useId();
  const [typeFilter, setTypeFilter] = useState<string>(defaultTypeFilter);
  const [query, setQuery] = useState<string>("");
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);

  const debouncedQuery = useDebounce(query, 300);
  const trimmed = debouncedQuery.trim();
  const hasMinChars = trimmed.length >= 2;
  const typesParam = typeFilter === "all" ? undefined : typeFilter;

  const { data: results = [], isLoading, isError } = useCatalogGraphSearch(trimmed, typesParam, 10, hasMinChars);

  const selectCandidate = (candidate: GraphRootSearchResult) => {
    setIsOpen(false);
    setActiveIndex(-1);
    onSelect(candidate.entity_type, candidate.entity_id);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!hasMinChars || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setIsOpen(true);
      setActiveIndex(prev => (prev + 1 < results.length ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setIsOpen(true);
      setActiveIndex(prev => (prev - 1 >= 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter" && isOpen && activeIndex >= 0 && activeIndex < results.length) {
      e.preventDefault();
      selectCandidate(results[activeIndex]);
    }
  };

  const activeOptionId =
    isOpen && activeIndex >= 0 && activeIndex < results.length ? `${listboxId}-option-${activeIndex}` : undefined;

  return (
    <div className="space-y-3" data-testid="graph-root-picker">
      <div className="flex flex-col gap-2 sm:flex-row">
        <Select
          value={typeFilter}
          onValueChange={val => {
            setTypeFilter(val);
            setActiveIndex(-1);
          }}
        >
          <SelectTrigger className="w-full sm:w-44" aria-label={t("pickerTypeLabel")} data-testid="graph-picker-type">
            <SelectValue placeholder={t("pickerTypeLabel")} />
          </SelectTrigger>
          <SelectContent>
            {PICKER_TYPES.map(pt => (
              <SelectItem key={pt} value={pt}>
                {pt === "all" ? t("pickerTypeAll") : t(`nodeTypes.${pt}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            role="combobox"
            aria-expanded={isOpen && hasMinChars}
            aria-controls={listboxId}
            aria-activedescendant={activeOptionId}
            aria-autocomplete="list"
            value={query}
            placeholder={t("pickerInputPlaceholder")}
            data-testid="graph-picker-input"
            className="flex h-9 w-full rounded-md border border-input bg-transparent py-1 pl-9 pr-3 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            onFocus={() => setIsOpen(true)}
            onChange={e => {
              setQuery(e.target.value);
              setIsOpen(true);
              setActiveIndex(-1);
            }}
            onKeyDown={handleKeyDown}
          />
        </div>
      </div>

      {query.trim().length > 0 && query.trim().length < 2 && (
        <p className="text-xs text-muted-foreground" data-testid="graph-picker-min-chars">
          {t("pickerMinChars")}
        </p>
      )}

      {isOpen && hasMinChars && (
        <div
          id={listboxId}
          role="listbox"
          data-testid="graph-picker-listbox"
          className="max-h-72 overflow-y-auto rounded-lg border border-border bg-card shadow-sm"
        >
          {isLoading ? (
            <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{t("pickerLoading")}</span>
            </div>
          ) : isError ? (
            <div className="px-3 py-3 text-xs text-destructive" data-testid="graph-picker-error">
              {t("pickerError")}
            </div>
          ) : results.length === 0 ? (
            <div className="px-3 py-3 text-xs text-muted-foreground" data-testid="graph-picker-empty">
              {t("pickerNoResults")}
            </div>
          ) : (
            results.map((item, idx) => {
              const optionId = `${listboxId}-option-${idx}`;
              const isSelected = idx === activeIndex;
              return (
                <button
                  key={`${item.entity_type}:${item.entity_id}`}
                  id={optionId}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  data-testid={`graph-picker-option-${item.entity_type}:${item.entity_id}`}
                  className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/60 ${
                    isSelected ? "bg-muted" : ""
                  }`}
                  onClick={() => selectCandidate(item)}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-foreground">{item.label}</div>
                    {item.subtitle && <div className="truncate text-xs text-muted-foreground">{item.subtitle}</div>}
                  </div>
                  <Badge variant="outline" className="shrink-0 text-[10px] uppercase">
                    {t(`nodeTypes.${item.entity_type}`)}
                  </Badge>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
