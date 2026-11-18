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

"use client";

import { Puzzle, Factory, Ruler, User } from "lucide-react";
import { getCoverTimestamp, getCoverUrl } from "@/lib/utils";
import { DiscoveryPivot } from "./discovery-pivot";

interface ExtendedMetadataPuzzleProps {
  meta: Record<string, unknown>;
}

/**
 * Extract normalized puzzle fields and cover URL from metadata.
 *
 * @param meta - The manifestation metadata record
 * @returns Normalized puzzle fields and cover URL
 */
function extractPuzzleFields(meta: Record<string, unknown>) {
  const cleanStr = (v: unknown): string | undefined => (typeof v === "string" && v.trim() !== "" ? v : undefined);
  const rawPieceCount = meta["piece_count"];
  const pieceCount = typeof rawPieceCount === "number" ? rawPieceCount : cleanStr(rawPieceCount);
  const dimensions = cleanStr(meta["dimensions"]);
  const manufacturer = cleanStr(meta["manufacturer"]);
  const artist = cleanStr(meta["artist"]);
  const puzzleType = cleanStr(meta["puzzle_type"]);
  const timestamp = getCoverTimestamp(meta);
  const coverUrl = getCoverUrl(meta["cover_url"] as string | undefined, timestamp);
  return { pieceCount, dimensions, manufacturer, artist, puzzleType, coverUrl };
}

/** Whether the metadata carries any displayable puzzle fields or cover. */
export function hasPuzzleMetadata(meta: Record<string, unknown>): boolean {
  const { pieceCount, dimensions, manufacturer, artist, puzzleType, coverUrl } = extractPuzzleFields(meta);
  return Boolean(pieceCount || dimensions || manufacturer || artist || puzzleType || coverUrl);
}

/**
 * Extended metadata component for puzzle items.
 *
 * @param props - Component props
 * @param props.meta - The metadata record
 * @returns {JSX.Element | null} The component or null if no puzzle metadata
 */
export function ExtendedMetadataPuzzle({ meta }: ExtendedMetadataPuzzleProps) {
  const { pieceCount, dimensions, manufacturer, artist, puzzleType, coverUrl } = extractPuzzleFields(meta);

  if (!hasPuzzleMetadata(meta)) {
    return null;
  }

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      {coverUrl && (
        <div className="flex justify-center mb-4">
          <div className="w-full max-w-[300px] aspect-video rounded-xl overflow-hidden shadow-md border bg-secondary/30">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={coverUrl} alt="Puzzle Box" className="h-full w-full object-cover" />
          </div>
        </div>
      )}
      <h3 className="font-bold text-lg text-foreground font-serif">Puzzle Details</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {pieceCount && (
          <div className="flex flex-col gap-2 p-3 bg-background rounded-lg border">
            <Puzzle className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{pieceCount} Pieces</span>
          </div>
        )}
        {dimensions && (
          <div className="flex flex-col gap-2 p-3 bg-background rounded-lg border">
            <Ruler className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{dimensions}</span>
          </div>
        )}
        {manufacturer && (
          <DiscoveryPivot
            type="publishers"
            value={manufacturer}
            className="flex flex-col gap-2 p-3 bg-background rounded-lg border hover:bg-muted/50 transition-colors"
          >
            <Factory className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{manufacturer}</span>
          </DiscoveryPivot>
        )}
        {artist && (
          <DiscoveryPivot
            type="q"
            value={artist}
            className="flex flex-col gap-2 p-3 bg-background rounded-lg border hover:bg-muted/50 transition-colors"
          >
            <User className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{artist}</span>
          </DiscoveryPivot>
        )}
      </div>
      {puzzleType && (
        <div className="mt-4">
          <DiscoveryPivot type="tags" value={puzzleType} badgeVariant="secondary" className="capitalize" />
        </div>
      )}
    </div>
  );
}
