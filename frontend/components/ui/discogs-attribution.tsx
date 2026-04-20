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

import Link from "next/link";
import { Badge } from "@/components/ui/badge";

/**
 * Component to display mandatory attribution to Discogs.
 * Required per Discogs API Terms of Use for any public facing apps.
 *
 * @returns {JSX.Element} The rendered attribution badge.
 */
export function DiscogsAttribution() {
  return (
    <div className="flex items-center justify-center pt-2 pb-1 w-full">
      <Link
        href="https://www.discogs.com"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <span>Source</span>
        <Badge
          variant="outline"
          className="font-semibold bg-yellow-500/10 text-yellow-700 hover:bg-yellow-500/20 border-yellow-200 dark:border-yellow-900"
        >
          Discogs
        </Badge>
      </Link>
    </div>
  );
}
