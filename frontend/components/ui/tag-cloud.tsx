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
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { DiscoveryPivot } from "@/components/item/discovery-pivot";

export interface TagItem {
  name: string;
  source?: string;
}

export type TagInput = string | TagItem;

export interface TagCloudProps {
  tags: TagInput[];
  maxInitial?: number;
  className?: string;
  chipClassName?: string;
  pivotType?: "tags" | "genres" | "publishers" | "q";
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
  renderTag?: (tag: TagItem, index: number) => React.ReactNode;
}

/**
 * Format tag source for human-readable display in tooltips.
 */
function formatSourceLabel(source?: string): string {
  if (!source) return "Source: Catalog Ingestion";
  const s = source.toLowerCase();
  if (s.includes("discogs")) return "Source: Discogs (Style/Genre)";
  if (s.includes("openlibrary")) return "Source: OpenLibrary (Subject)";
  if (s.includes("google")) return "Source: Google Books";
  if (s.includes("user")) return "Source: User Curation";
  return `Source: ${source}`;
}

/**
 * Responsive, compact tag cloud with "+X more" folding and provenance tooltips.
 */
export function TagCloud({
  tags,
  maxInitial = 10,
  className = "",
  chipClassName = "",
  pivotType,
  badgeVariant = "secondary",
  renderTag,
}: TagCloudProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!tags || tags.length === 0) {
    return null;
  }

  const normalizedTags: TagItem[] = tags.map(tag => (typeof tag === "string" ? { name: tag } : tag));

  const shouldFold = normalizedTags.length > maxInitial;
  const visibleTags = isExpanded || !shouldFold ? normalizedTags : normalizedTags.slice(0, maxInitial);
  const remainingCount = normalizedTags.length - maxInitial;

  return (
    <div className={cn("space-y-2", className)} data-testid="tag-cloud">
      <div className="flex flex-wrap items-center gap-1.5" role="list" aria-label="Tags">
        {visibleTags.map((tag, idx) => {
          if (renderTag) {
            return <React.Fragment key={`${tag.name}-${idx}`}>{renderTag(tag, idx)}</React.Fragment>;
          }

          const sourceTooltip = formatSourceLabel(tag.source);

          if (pivotType) {
            return (
              <DiscoveryPivot
                key={`${tag.name}-${idx}`}
                type={pivotType}
                value={tag.name}
                title={sourceTooltip}
                badgeVariant={badgeVariant}
                className={chipClassName}
              />
            );
          }

          return (
            <span
              key={`${tag.name}-${idx}`}
              role="listitem"
              property="sioc:topic"
              content={tag.name}
              title={sourceTooltip}
              className={cn(
                "inline-flex items-center rounded-md bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 ring-1 ring-inset ring-orange-600/10 dark:bg-orange-400/10 dark:text-orange-400 dark:ring-orange-400/20 cursor-default transition-colors",
                chipClassName
              )}
            >
              {tag.name}
            </span>
          );
        })}

        {shouldFold && (
          <button
            type="button"
            onClick={() => setIsExpanded(prev => !prev)}
            aria-expanded={isExpanded}
            className="inline-flex items-center gap-1 rounded-md bg-muted/60 hover:bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-all duration-150 cursor-pointer border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary"
            data-testid="tag-cloud-toggle"
          >
            {isExpanded ? (
              <>
                <span>Show less</span>
                <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                <span>+{remainingCount} more</span>
                <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
