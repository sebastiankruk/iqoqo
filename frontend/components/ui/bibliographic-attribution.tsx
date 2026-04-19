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
import { cn } from "@/lib/utils";

/**
 * Component to display attribution for the bibliographic metadata providers.
 *
 * @param {object} props - Component props
 * @param {string} [props.source] - The internal identifier for the data source (e.g., 'google_books', 'discogs').
 * @param {boolean} [props.centered=true] - Whether to center the attribution.
 * @returns {JSX.Element | null} The rendered attribution badge.
 */
export function BibliographicAttribution({ source, centered = true }: { source?: string; centered?: boolean }) {
  if (!source) return null;

  const providers: Record<string, { label: string; href: string; color: string; border: string }> = {
    google_books: {
      label: "Google Books",
      href: "https://books.google.com/",
      color: "bg-blue-500/10 text-blue-700 dark:text-blue-400 hover:bg-blue-500/20",
      border: "border-blue-200 dark:border-blue-900",
    },
    open_library: {
      label: "Open Library",
      href: "https://openlibrary.org/",
      color: "bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20",
      border: "border-amber-200 dark:border-amber-900",
    },
    discogs: {
      label: "Discogs",
      href: "https://www.discogs.com/",
      color: "bg-neutral-500/10 text-neutral-700 dark:text-neutral-400 hover:bg-neutral-500/20",
      border: "border-neutral-200 dark:border-neutral-800",
    },
    tmdb: {
      label: "TMDB",
      href: "https://www.themoviedb.org/",
      color: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20",
      border: "border-emerald-200 dark:border-emerald-900",
    },
    bgg: {
      label: "BoardGameGeek",
      href: "https://boardgamegeek.com/",
      color: "bg-orange-500/10 text-orange-700 dark:text-orange-400 hover:bg-orange-500/20",
      border: "border-orange-200 dark:border-orange-900",
    },
  };

  const config = providers[source.toLowerCase().replace(" ", "_")];
  if (!config) return null;

  return (
    <div className={cn("flex items-center pt-2 pb-1 w-full", centered ? "justify-center" : "justify-start")}>
      <div className="inline-flex items-center gap-1.5 text-[0.65rem] uppercase tracking-wider font-semibold text-muted-foreground/60">
        <span>Source</span>
        <Link
          href={config.href}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center hover:opacity-80 transition-opacity"
        >
          <Badge variant="outline" className={cn("text-[10px] font-bold py-0 h-5 lowercase px-2", config.color, config.border)}>
            {config.label}
          </Badge>
        </Link>
      </div>
    </div>
  );
}

// Keep the old name as a wrapper for backward compatibility if needed, 
// but pointing to the two primary book sources by default.
/**
 * Compatibility shim for the old IsbnDbAttribution name.
 * Renders both primary book metadata providers.
 *
 * @returns {JSX.Element} The rendered attribution badges.
 */
export function IsbnDbAttribution() {
  return (
    <div className="space-y-1">
      <BibliographicAttribution source="google_books" />
      <BibliographicAttribution source="open_library" />
    </div>
  );
}
