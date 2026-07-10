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

import { useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Globe, Check } from "lucide-react";
import { useLocale } from "next-intl";

/**
 * Component to switch between languages (English and Polish).
 *
 * @returns {JSX.Element} The component.
 */
export function LanguageToggle() {
  const router = useRouter();
  const locale = useLocale();

  const setLanguage = (locale: string) => {
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=31536000; SameSite=Lax`;
    router.refresh();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex h-9 w-9 items-center justify-center rounded-full border border-transparent bg-transparent text-primary-foreground/80 transition-colors hover:border-primary-foreground/40 hover:text-primary-foreground dark:text-white/90 dark:hover:text-white outline-none">
          <Globe className="h-4 w-4" />
          <span className="sr-only">Toggle language</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="dark:bg-[#0a0c10] dark:border-white/10">
        <DropdownMenuItem
          onClick={() => setLanguage("en")}
          className="cursor-pointer flex items-center justify-between gap-2"
        >
          <span>English</span>
          {locale === "en" && <Check className="h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage("pl")}
          className="cursor-pointer flex items-center justify-between gap-2"
        >
          <span>Polski</span>
          {locale === "pl" && <Check className="h-4 w-4" />}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
