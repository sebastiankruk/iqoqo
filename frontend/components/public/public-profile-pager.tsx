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
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** How many page links to show either side of the current one. */
const SIBLINGS = 2;

/**
 * Build the visible page numbers with ellipsis gaps for a long range.
 *
 * Keeping the first and last pages reachable matters more than a compact
 * control: a collector with hundreds of items should be able to jump to the
 * end, not click "next" forty times.
 *
 * @param current - The 1-based page currently displayed.
 * @param total - The 1-based total page count.
 * @returns Page numbers and `null` markers where a gap was elided.
 */
function pageWindow(current: number, total: number): (number | null)[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const out: (number | null)[] = [1];
  const start = Math.max(2, current - SIBLINGS);
  const end = Math.min(total - 1, current + SIBLINGS);
  if (start > 2) out.push(null);
  for (let p = start; p <= end; p += 1) out.push(p);
  if (end < total - 1) out.push(null);
  out.push(total);
  return out;
}

export interface PublicProfilePagerProps {
  /** Public username whose collection is being paged. */
  username: string;
  /** 1-based current page. */
  currentPage: number;
  /** 1-based total page count. */
  totalPages: number;
  /** Number of items rendered on this page. */
  shown: number;
  /** Total items across all pages, when the API reported it. */
  total?: number;
}

/**
 * Page navigation for a public profile collection.
 *
 * The public items endpoint paginates server-side, so without this control a
 * collector with more public items than one page could see had no route to the
 * rest — the first 24 were simply all that ever rendered.
 *
 * Renders nothing for a single page, so a small collection is not given
 * controls that do nothing.
 *
 * @param props - Component props.
 * @param props.username - Public username whose collection is paged.
 * @param props.currentPage - 1-based current page.
 * @param props.totalPages - 1-based total page count.
 * @param props.shown - Items rendered on this page.
 * @param props.total - Total items across all pages, when reported.
 * @returns The pager, or null when there is only one page.
 */
export function PublicProfilePager({ username, currentPage, totalPages, shown, total }: PublicProfilePagerProps) {
  if (totalPages <= 1) {
    return null;
  }

  const href = (page: number) => `/u/${encodeURIComponent(username)}${page > 1 ? `?page=${page}` : ""}`;
  const window = pageWindow(currentPage, totalPages);

  return (
    <nav aria-label="Collection pages" className="mt-8 flex flex-col items-center gap-3">
      {total !== undefined && total > 0 ? (
        <p className="text-sm text-muted-foreground">
          Showing {(currentPage - 1) * shown + 1}–{(currentPage - 1) * shown + shown} of {total}
        </p>
      ) : null}
      <div className="flex items-center gap-1">
        {currentPage > 1 ? (
          <Button asChild variant="outline" size="sm" aria-label="Previous page">
            <Link href={href(currentPage - 1)}>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Previous page</span>
            </Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled aria-label="Previous page">
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Previous page</span>
          </Button>
        )}

        {window.map((page, i) =>
          page === null ? (
            <span key={`gap-${i}`} className="px-2 text-sm text-muted-foreground" aria-hidden="true">
              …
            </span>
          ) : (
            <Button
              key={page}
              asChild
              variant={page === currentPage ? "default" : "outline"}
              size="sm"
              aria-current={page === currentPage ? "page" : undefined}
              className={cn("min-w-9", page === currentPage && "font-semibold")}
            >
              <Link href={href(page)}>{page}</Link>
            </Button>
          )
        )}

        {currentPage < totalPages ? (
          <Button asChild variant="outline" size="sm" aria-label="Next page">
            <Link href={href(currentPage + 1)}>
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Next page</span>
            </Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled aria-label="Next page">
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Next page</span>
          </Button>
        )}
      </div>
    </nav>
  );
}
