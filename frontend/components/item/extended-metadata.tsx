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

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { isAudioMedia } from "@/lib/utils";
import { ExtendedMetadataVideo } from "./extended-metadata-video";
import { ExtendedMetadataBoardGame } from "./extended-metadata-boardgame";
import { ExtendedMetadataPuzzle } from "./extended-metadata-puzzle";

interface ExtendedMetadataProps {
  meta: Record<string, unknown>;
  owner_name?: string | null;
  owner_count?: number;
}

/**
 * Extended metadata component.
 *
 * @param root0 - The props object
 * @param root0.meta - The metadata to display
 * @param root0.owner_name - The owner name to display
 * @param root0.owner_count - The number of owners for this manifestation
 * @returns {JSX.Element | null} The component or null if no metadata
 */
export function ExtendedMetadata({ meta, owner_name, owner_count }: ExtendedMetadataProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!meta) return null;

  const description = (meta["description"] as string | undefined) || (meta["Description"] as string | undefined);
  const categories =
    ((meta["categories"] as string[] | undefined) || (meta["Categories"] as string[] | undefined)) ?? [];

  const format = meta["format"] as string | undefined;
  const isAudio = isAudioMedia(format);
  const isVideo = ["dvd", "bluray", "video", "moving image"].includes(format?.toLowerCase() || "");
  const isBoardGame = ["boardgame", "board_game", "three-dimensional object"].includes(format?.toLowerCase() || "");
  const isPuzzle = ["puzzle", "jigsaw", "jigsaw puzzle"].includes(format?.toLowerCase() || "");

  const trackList = meta["track_list"] as
    | Array<{ position: string; title: string; duration_seconds: number }>
    | undefined;

  const hiddenKeys = new Set([
    "title",
    "Title",
    "author",
    "authors",
    "Authors",
    "description",
    "Description",
    "categories",
    "Categories",
    "cover_status",
    "cover_source",
    "cover_url",
    "cover_status_updated_at",
    "local_cover",
    "tags",
    "year",
    "Year",
    "pages",
    "Pages",
    "subtitle",
    "Subtitle",
    "track_list",
    "tracks",
    "Tracks",
    "additional_images",
    "format",
    "publisher",
    "label",
    "barcode",
    "isbn",
    "catalog_number",
    "matrix_number",
    "pressing_number",
    "disc_count",
    "min_players",
    "max_players",
    "playing_time",
    "playtime",
    "min_playtime",
    "max_playtime",
    "mechanics",
    "cast",
    "directors",
    "runtime",
    "MinPlayers",
    "MaxPlayers",
    "PlayTime",
    "Mechanics",
    "Cast",
    "Director",
    "Runtime",
    "piece_count",
    "dimensions",
    "artist",
    "manufacturer",
    "puzzle_type",
  ]);

  const extraKeys = Object.entries(meta)
    .filter(([key, value]) => {
      const excludedKeys = ["id", "manifestation_id", "cover_url", "image", "cover_status", "cover"];
      if (excludedKeys.includes(key.toLowerCase()) || hiddenKeys.has(key)) return false;

      const val = String(value).toLowerCase();
      if (!value || val === "unknown" || val === "n/a" || val === "none" || val === "") return false;

      return typeof value !== "object";
    })
    .map(([key]) => key);

  if (
    !description &&
    categories.length === 0 &&
    !isAudio &&
    !isVideo &&
    !isBoardGame &&
    !isPuzzle &&
    !trackList &&
    extraKeys.length === 0 &&
    !owner_name &&
    !owner_count
  )
    return null;

  return (
    <div className="space-y-4 py-4">
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {categories.map(cat => (
            <Badge key={cat} variant="secondary">
              {cat}
            </Badge>
          ))}
        </div>
      )}

      {description && (
        <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground bg-muted/20 p-4 rounded-xl border border-border/40">
          <p>{description}</p>
        </div>
      )}

      {isVideo && <ExtendedMetadataVideo meta={meta} />}
      {isBoardGame && <ExtendedMetadataBoardGame meta={meta} />}
      {isPuzzle && <ExtendedMetadataPuzzle meta={meta} />}

      {isAudio && (
        <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
          <h3 className="font-bold text-lg text-foreground font-serif">Release Information</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
            {Boolean(meta["label"] || meta["publisher"]) && (
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">
                  Label / Publisher
                </span>
                <span className="font-semibold">{String(meta["label"] || meta["publisher"])}</span>
              </div>
            )}
            {Boolean(meta["catalog_number"] || meta["Catalog Number"]) && (
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Catalog #</span>
                <span className="font-semibold">{String(meta["catalog_number"] || meta["Catalog Number"])}</span>
              </div>
            )}
            {Boolean(meta["matrix_number"] || meta["Matrix / Runout"]) && (
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">
                  Matrix / Runout
                </span>
                <span className="font-mono text-xs">{String(meta["matrix_number"] || meta["Matrix / Runout"])}</span>
              </div>
            )}
            {Boolean(meta["disc_count"]) && (
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Discs</span>
                <span className="font-semibold">{String(meta["disc_count"])}</span>
              </div>
            )}
            {format && (
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">
                  Media Format
                </span>
                <span className="font-semibold uppercase">{format}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {trackList && trackList.length > 0 && (
        <div className="rounded-xl border bg-card/50 p-5 shadow-sm">
          <h3 className="font-bold text-lg mb-4 text-foreground font-serif">Tracklist</h3>
          <div className="divide-y border-t border-muted/60">
            {trackList.map(track => (
              <div
                key={track.position}
                className="py-3 flex justify-between text-sm items-center hover:bg-muted/30 px-3 -mx-3 rounded-lg transition-colors group"
              >
                <div className="flex gap-4">
                  <span className="text-muted-foreground/60 w-8 font-mono group-hover:text-primary transition-colors">
                    {track.position}
                  </span>
                  <span className="font-semibold">{track.title}</span>
                </div>
                {track.duration_seconds > 0 && (
                  <span className="text-muted-foreground font-mono text-xs">
                    {Math.floor(track.duration_seconds / 60)}:
                    {(track.duration_seconds % 60).toString().padStart(2, "0")}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {(extraKeys.length > 0 || owner_name) && (
        <div className="border rounded-xl p-2 bg-muted/10">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between h-10 hover:bg-muted/20"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span className="font-bold text-xs uppercase tracking-widest text-muted-foreground">
              Additional Details
            </span>
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>

          {isExpanded && (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 p-4 text-sm bg-background/50 rounded-lg mt-2 border border-border/40">
              {(owner_name || owner_count) && (
                <div className="flex flex-col gap-1 pb-2 border-b border-border/20">
                  <dt className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Owner</dt>
                  <dd className="font-medium text-foreground">
                    {owner_name}
                    {owner_count && owner_count > 1 && (
                      <span className={`text-muted-foreground ${owner_name && "ml-1"}`}>
                        (<strong>{owner_count}</strong> owners)
                      </span>
                    )}
                  </dd>
                </div>
              )}
              {extraKeys.map(key => (
                <div key={key} className="flex flex-col gap-1 pb-2 border-b border-border/20 last:border-0">
                  <dt className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">
                    {key.replace(/_/g, " ")}
                  </dt>
                  <dd className="font-medium text-foreground break-words">{String(meta[key])}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </div>
  );
}
