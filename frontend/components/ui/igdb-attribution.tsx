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
 * Component to display mandatory attribution to IGDB.
 * Required per IGDB API Terms of Use for any public facing apps.
 * @returns {JSX.Element} The rendered attribution component.
 */
export function IgdbAttribution() {
  return (
    <div className="flex items-center justify-center pt-2 pb-1 w-full">
      <Link
        href="https://www.igdb.com"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <span>Powered by</span>
        <Badge
          variant="outline"
          className="font-semibold bg-[#9146FF]/10 text-[#9146FF] hover:bg-[#9146FF]/20 border-[#9146FF]/30 dark:border-[#9146FF]/50"
        >
          IGDB
        </Badge>
      </Link>
    </div>
  );
}
