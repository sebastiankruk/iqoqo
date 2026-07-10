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
import { Github } from "lucide-react";
import { useTranslations } from "next-intl";

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
              <Github className="w-4 h-4 mr-2" />
              {t("github")}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
