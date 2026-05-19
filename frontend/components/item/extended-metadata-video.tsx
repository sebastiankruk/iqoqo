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
import { TmdbAttribution } from "@/components/ui/tmdb-attribution";
import { getCoverTimestamp, getCoverUrl } from "@/lib/utils";
import { DiscoveryPivot } from "./discovery-pivot";

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
  const timestamp = getCoverTimestamp(meta);
  const coverUrl = getCoverUrl(meta["cover_url"] as string | undefined, timestamp);

  if (!cast?.length && !directors?.length && !runtime && meta.Source !== "TMDB" && !coverUrl) return null;

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      {coverUrl && (
        <div className="flex justify-center mb-4">
          <div className="w-full max-w-[240px] aspect-[2/3] rounded-xl overflow-hidden shadow-md border bg-secondary/30">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={coverUrl} alt="Movie Poster" className="h-full w-full object-cover" />
          </div>
        </div>
      )}
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
            <div className="flex flex-wrap gap-1">
              {directors.map((d, idx) => (
                <span key={d}>
                  <DiscoveryPivot type="q" value={d} variant="link" className="font-semibold" />
                  {idx < directors.length - 1 && <span className="text-muted-foreground/60">,&nbsp;</span>}
                </span>
              ))}
            </div>
          </div>
        )}
        {cast && cast.length > 0 && (
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-muted-foreground text-[10px] uppercase font-bold tracking-widest">Cast</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {cast.map(c => (
                <DiscoveryPivot key={c} type="q" value={c} badgeVariant="secondary" className="font-normal" />
              ))}
            </div>
          </div>
        )}
      </div>

      {meta.Source === "TMDB" && (
        <div className="mt-6 pt-4 border-t border-border/50">
          <TmdbAttribution />
        </div>
      )}
    </div>
  );
}
