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
import { Badge } from "@/components/ui/badge";
import { BggAttribution } from "@/components/ui/bgg-attribution";

interface ExtendedMetadataBoardGameProps {
  meta: Record<string, unknown>;
}

/**
 * Extended metadata component for board game items.
 *
 * @param props - Component props
 * @param props.meta - The metadata record
 * @returns {JSX.Element | null} The component or null if no relevant metadata
 */
export function ExtendedMetadataBoardGame({ meta }: ExtendedMetadataBoardGameProps) {
  const minPlayers = (meta.min_players || meta.MinPlayers) as number | undefined;
  const maxPlayers = (meta.max_players || meta.MaxPlayers) as number | undefined;
  const playingTime = (meta.playing_time || meta.playtime || meta.max_playtime || meta.PlayTime) as number | undefined;
  const mechanics = (meta.mechanics || meta.Mechanics) as string[] | undefined;
  const source = meta.Source as string | undefined;

  if (!minPlayers && !maxPlayers && !playingTime && !mechanics?.length && source !== "BGG") return null;

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      <h3 className="font-bold text-lg text-foreground font-serif">Game Details</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
        {(minPlayers || maxPlayers) && (
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Players</span>
            <span className="font-semibold">
              {minPlayers === maxPlayers ? minPlayers : `${minPlayers || "?"} - ${maxPlayers || "?"}`}
            </span>
          </div>
        )}
        {playingTime && (
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Playtime</span>
            <span className="font-semibold">{playingTime} min</span>
          </div>
        )}
        {mechanics && mechanics.length > 0 && (
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Mechanics</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {mechanics.map(m => (
                <Badge key={m} variant="secondary" className="font-normal">
                  {m}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {source === "BGG" && (
        <div className="mt-4 pt-4 border-t border-border/50">
          <BggAttribution />
        </div>
      )}
    </div>
  );
}
