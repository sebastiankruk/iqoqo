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
import { EyeOff, Users } from "lucide-react";
import type { Item } from "@/types/frbr";

/** Props for SidebarStatusBadges component */
export interface SidebarStatusBadgesProps {
  collectionStatusInfo: { label: string; class: string };
  progressStatusInfo: { label: string; class: string };
  isHidden?: boolean;
  visibility?: "private" | "friends_only" | "shared" | "public";
  item?: Item;
}

/**
 * Status badges display region of ItemSidebar, rendering collection status,
 * personal progress, and hidden status pill.
 *
 * @param props - Props object
 * @returns {JSX.Element} Rendered badges block
 */
export function SidebarStatusBadges({
  collectionStatusInfo,
  progressStatusInfo,
  isHidden,
  visibility,
  item,
}: SidebarStatusBadgesProps) {
  const itemVisibility = visibility ?? item?.visibility;
  const isFriendsOnly = itemVisibility === "friends_only";
  const hidden = isFriendsOnly ? false : (isHidden ?? item?.is_hidden);

  return (
    <div className="flex flex-wrap justify-center gap-2 px-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all ${collectionStatusInfo.class}`}
        title="Collection Availability"
      >
        <span className="h-1 w-1 rounded-full bg-current opacity-70" />
        {collectionStatusInfo.label?.toUpperCase() || "UNKNOWN"}
      </span>
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all ${progressStatusInfo.class}`}
        title="Personal Progress"
      >
        <span className="h-1 w-1 rounded-full bg-current opacity-70" />
        {progressStatusInfo.label?.toUpperCase() || "UNKNOWN"}
      </span>
      {isFriendsOnly && (
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all bg-sky-950 text-sky-200 ring-sky-700 dark:bg-sky-900/60 dark:text-sky-300 dark:ring-sky-600"
          title="Visible only to accepted friends"
          data-testid="badge-friends-only"
        >
          <Users className="h-3 w-3" />
          FRIENDS ONLY
        </span>
      )}
      {hidden && (
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all bg-zinc-900 text-zinc-100 ring-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-300"
          title="Item is hidden from your public profile"
          data-testid="badge-hidden"
        >
          <EyeOff className="h-3 w-3" />
          HIDDEN
        </span>
      )}
    </div>
  );
}
