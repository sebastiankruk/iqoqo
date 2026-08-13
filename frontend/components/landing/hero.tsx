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

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

/**
 * GitHub SVG icon component.
 *
 * @param {object} props - Component props.
 * @param {string} [props.className] - CSS class names.
 * @returns {JSX.Element} The rendered SVG icon.
 */
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg role="img" viewBox="0 0 24 24" fill="currentColor" className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

/**
 * Hero section component.
 *
 * @returns {JSX.Element} The component
 */
export function Hero() {
  const t = useTranslations("Hero");

  return (
    <div className="relative w-full h-[420px] flex items-center justify-center overflow-hidden rounded-xl mb-12">
      <div className="absolute inset-0 z-0">
        <Image
          src="/inside-library-photo.png"
          alt="Inside the library"
          fill
          className="object-cover opacity-40"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
      </div>

      <div className="relative z-10 text-center px-4 max-w-3xl">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">{t("title")}</h1>
        <p className="text-xl text-muted-foreground mb-8">{t("description")}</p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Button
            asChild
            size="sm"
            className="bg-accent text-accent-foreground hover:opacity-90 font-bold border-none shadow-md"
          >
            <Link href="/register">{t("startCatalog")}</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/collection">{t("browseInstance")}</Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="text-muted-foreground hover:text-foreground">
            <Link href="https://github.com/sebastiankruk/iqoqo" target="_blank" rel="noopener noreferrer">
              <GithubIcon className="w-4 h-4 mr-2" />
              {t("github")}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
