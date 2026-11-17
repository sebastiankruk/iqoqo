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

/**
 * Computes a bounded pagination window containing at most 10 page numbers:
 * page 1 (first), up to 8 pages centered around `currentPage`, and `totalPages` (last).
 *
 * @param currentPage - 1-based active page index.
 * @param totalPages - Total number of pages available.
 * @returns Sorted, deduplicated list of at most 10 page numbers.
 */
export function buildPaginationWindow(currentPage: number, totalPages: number): number[] {
  if (totalPages <= 0) return [];
  if (totalPages <= 10) {
    return Array.from({ length: totalPages }, (_, idx) => idx + 1);
  }

  const clampedCurrent = Math.min(Math.max(1, currentPage), totalPages);
  let start = Math.max(2, clampedCurrent - 3);
  let end = start + 7;

  if (end > totalPages - 1) {
    end = totalPages - 1;
    start = Math.max(2, end - 7);
  }

  const pages: number[] = [1];
  for (let p = start; p <= end; p += 1) {
    pages.push(p);
  }
  pages.push(totalPages);
  return pages;
}
