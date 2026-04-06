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
import { Badge } from "@/components/ui/badge";

interface ExtendedMetadataPuzzleProps {
  meta: Record<string, unknown>;
}

export function ExtendedMetadataPuzzle({ meta }: ExtendedMetadataPuzzleProps) {
  const pieceCount = meta["piece_count"] as number | string | undefined;
  const dimensions = meta["dimensions"] as string | undefined;
  const manufacturer = meta["manufacturer"] as string | undefined;
  const artist = meta["artist"] as string | undefined;
  const puzzleType = meta["puzzle_type"] as string | undefined;

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
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
          <div className="flex flex-col gap-2 p-3 bg-background rounded-lg border">
            <Factory className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{manufacturer}</span>
          </div>
        )}
        {artist && (
          <div className="flex flex-col gap-2 p-3 bg-background rounded-lg border">
            <User className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-semibold">{artist}</span>
          </div>
        )}
      </div>
      {puzzleType && (
        <div className="mt-4">
          <Badge variant="secondary" className="capitalize">
            {puzzleType}
          </Badge>
        </div>
      )}
    </div>
  );
}
