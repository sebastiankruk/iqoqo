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
"use client";

import Link from "next/link";

/**
 * Blurred-cover hero banner with breadcrumb navigation.
 *
 * @param root0 - The props object
 * @param root0.coverUrl - The cover URL
 * @param root0.title - The title
 * @returns {JSX.Element} The component
 */
export function HeroBanner({ coverUrl, title }: { coverUrl?: string; title?: string }) {
  return (
    <div className="relative h-[200px] w-full overflow-hidden bg-primary dark:bg-[#040608]">
      {coverUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={coverUrl}
          alt=""
          className="absolute inset-0 h-full w-full scale-110 object-cover opacity-40 blur-xl"
        />
      )}
      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/60 via-primary/70 to-primary/90 dark:from-[#040608]/60 dark:via-[#040608]/70 dark:to-[#040608]/90" />

      {/* Breadcrumb */}
      <div className="relative z-10 mx-auto flex h-full max-w-6xl flex-col justify-end px-6 pb-16">
        <nav className="flex items-center gap-2 text-xs text-primary-foreground/80" aria-label="Breadcrumb">
          <Link href="/" className="transition-colors hover:text-primary-foreground">
            Library
          </Link>
          <span>/</span>
          <Link href="/collection" className="transition-colors hover:text-primary-foreground">
            Collection
          </Link>
          <span>/</span>
          <span className="text-primary-foreground/90">{title ?? "Item"}</span>
        </nav>
      </div>
    </div>
  );
}
