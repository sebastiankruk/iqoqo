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
 * Component to display attribution for the book metadata providers
 * currently used by the backend fetcher (Google Books and Open Library).
 *
 * The exported name is kept for compatibility with existing imports.
 *
 * @returns {JSX.Element} The rendered attribution badges.
 */
export function IsbnDbAttribution() {
  return (
    <div className="flex items-center justify-center pt-2 pb-1 w-full">
      <div className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <span>Powered by</span>
        <Link
          href="https://books.google.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center hover:text-foreground transition-colors"
        >
          <Badge
            variant="outline"
            className="font-semibold bg-blue-500/10 text-blue-700 hover:bg-blue-500/20 border-blue-200 dark:border-blue-900"
          >
            Google Books
          </Badge>
        </Link>
        <span aria-hidden="true">&amp;</span>
        <Link
          href="https://openlibrary.org/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center hover:text-foreground transition-colors"
        >
          <Badge
            variant="outline"
            className="font-semibold bg-amber-500/10 text-amber-700 hover:bg-amber-500/20 border-amber-200 dark:border-amber-900"
          >
            Open Library
          </Badge>
        </Link>
      </div>
    </div>
  );
}
