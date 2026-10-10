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
import * as React from "react";
import { BookOpen, Disc, Film, Gamepad2 } from "lucide-react";
import type { Item } from "@/types/frbr";
import { CoverProvenance } from "@/components/cover/cover-provenance";

/** Props for SidebarCover component */
export interface SidebarCoverProps {
  item: Item;
  coverUrl?: string;
  format: string;
  isAudio: boolean;
  isVideo: boolean;
  isGame: boolean;
  isBook: boolean;
}

/**
 * Cover display region of ItemSidebar, including format-based aspect ratio and fallback icons.
 *
 * @param props - Props object
 * @returns {JSX.Element} Rendered cover block
 */
export function SidebarCover({ item, coverUrl, isAudio, isVideo, isGame }: SidebarCoverProps) {
  const aspectClass = isAudio || isGame ? "aspect-square" : "aspect-[2/3]";
  const MediaIcon = isAudio ? Disc : isVideo ? Film : isGame ? Gamepad2 : BookOpen;

  return (
    <div className="-mt-28 w-full max-w-[220px] flex flex-col items-center">
      <div
        className={`relative ${aspectClass} w-full overflow-hidden rounded-lg shadow-xl ring-4 ring-card bg-secondary`}
      >
        {coverUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={coverUrl} alt={item.title ?? "Cover"} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center">
            <MediaIcon className="h-12 w-12 text-muted-foreground/30" />
          </div>
        )}
      </div>
      <CoverProvenance
        source={
          (item.manifestation_meta?.["cover_source"] as string | undefined) ??
          (item.meta?.["cover_source"] as string | undefined)
        }
        className="mt-2.5"
      />
    </div>
  );
}
