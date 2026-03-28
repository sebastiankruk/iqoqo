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

import { Calendar, BookOpen, Tag } from "lucide-react";
import type { Item } from "@/types/frbr";

/**
 * Title, authors, year, page count, and tag badges for an item.
 *
 * @param root0 - The props object
 * @param root0.item - The item
 * @returns {JSX.Element} The component
 */
export function ItemHeader({ item }: { item: Item }) {
  const work = item.work;
  const meta = item.manifestation_meta ?? {};
  const tags = (meta["tags"] as string[] | undefined) ?? [];
  const year = meta["Year"] as string | undefined;
  const pages = meta["Pages"] as string | undefined;
  const authors = work?.authors ?? item.authors ?? [];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-balance font-serif text-2xl font-bold leading-tight text-foreground sm:text-3xl">
            {work?.title ?? item.title ?? "Untitled"}
          </h1>
          {!!meta["Subtitle"] && (
            <h2 className="font-serif text-base font-light text-muted-foreground sm:text-lg">
              {meta["Subtitle"] as string}
            </h2>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-muted-foreground">
        {authors.length > 0 && <span className="font-medium text-foreground">{authors.join(", ")}</span>}
        {year && (
          <>
            <span className="text-border">&bull;</span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {year}
            </span>
          </>
        )}
        {pages && (
          <>
            <span className="text-border">&bull;</span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3.5 w-3.5" />
              {pages} pages
            </span>
          </>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {tags.map(tag => (
            <span
              key={tag}
              className="flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
            >
              <Tag className="h-3 w-3" />
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="h-px bg-border" />
    </div>
  );
}
