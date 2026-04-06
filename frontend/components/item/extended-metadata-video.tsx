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

interface ExtendedMetadataVideoProps {
  meta: Record<string, unknown>;
}

/**
 * Extended metadata component for video items.
 *
 * @param props - Component props
 * @param props.meta - The metadata record
 * @returns {JSX.Element | null} The component or null if no relevant metadata
 */
export function ExtendedMetadataVideo({ meta }: ExtendedMetadataVideoProps) {
  const cast = (meta.cast || meta.Cast) as string[] | undefined;
  const directors = (meta.directors || meta.Director) as string[] | undefined;
  const runtime = (meta.runtime || meta.Runtime) as number | undefined;

  if (!cast?.length && !directors?.length && !runtime) return null;

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      <h3 className="font-bold text-lg text-foreground font-serif">Video Details</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
        {runtime && (
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Runtime</span>
            <span className="font-semibold">{runtime} min</span>
          </div>
        )}
        {directors && directors.length > 0 && (
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Director(s)</span>
            <span className="font-semibold">{directors.join(", ")}</span>
          </div>
        )}
        {cast && cast.length > 0 && (
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Cast</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {cast.map(c => (
                <Badge key={c} variant="secondary" className="font-normal">
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
