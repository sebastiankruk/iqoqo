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

import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import type { Item } from "@/types/frbr";
import { isAudioMedia, getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { Disc, BookOpen, Calendar, Tag } from "lucide-react";

interface ItemHeaderProps {
  item: Item;
}

/**
 * Responsive item header component.
 *
 * @param props - Component props
 * @param props.item - The item to display
 * @returns {JSX.Element} The component
 */
export function ItemHeader({ item }: ItemHeaderProps) {
  const work = item.work;
  const meta = item.manifestation_meta ?? {};
  const tags = (meta["tags"] as string[] | undefined) ?? [];

  const title = work?.title ?? item.title ?? "Untitled";
  const authorDisplay = work?.authors?.join(", ") ?? item.authors?.join(", ") ?? "Unknown Artist/Author";

  const timestamp = getCoverTimestamp(meta);

  // Normalize cover URL handling for both external and local static paths
  const coverUrl =
    getCoverUrl(item.cover_url || undefined, timestamp) || (meta["cover_url"] as string | undefined) || "/file.svg";

  const format = (meta["format"] as string | undefined) || (meta["Format"] as string | undefined) || "book";
  const isAudio = isAudioMedia(format);
  const identifier = item.isbn || (meta["isbn"] as string | undefined) || (meta["barcode"] as string | undefined);
  const publisher = (meta["publisher"] as string | undefined) || (meta["label"] as string | undefined);
  const year = (meta["year"] as string | undefined) || (meta["Year"] as string | undefined);

  return (
    <div className="flex flex-col md:flex-row gap-6 lg:gap-10 mb-8 items-start">
      {/* Cover Image stacks at top on mobile, ensuring no collision with actions below */}
      <div
        className={`w-full md:w-1/3 lg:w-1/4 shrink-0 overflow-hidden rounded-xl shadow-2xl bg-muted relative ${isAudio ? "aspect-square" : "aspect-[2/3]"}`}
      >
        <Image
          src={coverUrl}
          alt={`Cover of ${title}`}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 33vw, 25vw"
          priority
          unoptimized={coverUrl.startsWith("http")}
        />
      </div>

      <div className="flex flex-col flex-1 w-full">
        {/* Status Pills immediately below image on mobile */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <Badge variant="default" className="capitalize px-3 py-1 text-xs font-semibold tracking-wide">
            {item.status?.replace("_", " ") ?? "Unknown"}
          </Badge>
          {isAudio && (
            <Badge
              variant="secondary"
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold uppercase tracking-wider"
            >
              <Disc className="h-3 w-3" />
              CD / Audio
            </Badge>
          )}
          {!isAudio && (
            <Badge
              variant="outline"
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold uppercase tracking-wider"
            >
              <BookOpen className="h-3 w-3" />
              Book
            </Badge>
          )}
        </div>

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {tags.map(tag => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full bg-secondary/50 px-2 py-0.5 text-[10px] font-medium text-secondary-foreground"
              >
                <Tag className="h-2.5 w-2.5" />
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Core details */}
        <div className="space-y-2 mb-6">
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-extrabold tracking-tight font-serif text-foreground leading-tight">
            {title}
          </h1>
          <h2 className="text-xl md:text-2xl text-muted-foreground font-medium">{authorDisplay}</h2>
        </div>

        {/* Quick Meta block */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-muted/30 p-5 rounded-2xl mb-8 border border-border/50">
          {identifier && (
            <div className="space-y-1">
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-widest">
                Identifier
              </span>
              <span className="font-mono text-xs">{identifier}</span>
            </div>
          )}
          {publisher && (
            <div className="space-y-1">
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-widest">
                {isAudio ? "Label" : "Publisher"}
              </span>
              <span className="font-semibold">{publisher}</span>
            </div>
          )}
          {year && (
            <div className="space-y-1">
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-widest flex items-center gap-1">
                <Calendar className="h-2.5 w-2.5" />
                Released
              </span>
              <span className="font-semibold">{year}</span>
            </div>
          )}
          {Boolean(meta["pages"] || meta["Pages"] || meta["tracks"] || meta["Tracks"]) && (
            <div className="space-y-1">
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-widest">
                {isAudio ? "Tracks" : "Pages"}
              </span>
              <span className="font-semibold">
                {String(meta["tracks"] || meta["Tracks"] || meta["pages"] || meta["Pages"])}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
