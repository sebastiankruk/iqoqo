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

import { APP_VERSION } from "@/lib/version";
import { useTranslations } from "next-intl";

/**
 * Site footer displaying the iqoqo brand name, open-source sponsorship links,
 * and the current UI version string.
 *
 * @returns {JSX.Element} The footer component
 */
export function Footer() {
  const t = useTranslations("Footer");
  const uiVersion = APP_VERSION;

  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <p className="text-xs text-muted-foreground">
          <span className="font-serif font-bold text-foreground">iqoqo</span> &middot; {t("libraryOfEverything")}{" "}
          &middot; {uiVersion} &middot;{" "}
          <a
            href="https://github.com/sponsors/sebastiankruk"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground transition-colors"
          >
            {t("githubSponsors")}
          </a>{" "}
          &middot;{" "}
          <a
            href="https://buymeacoffee.com/iqoqo"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground transition-colors"
          >
            {t("buyMeACoffee")}
          </a>
        </p>
        <p className="text-xs text-muted-foreground">{t("rules")}</p>
      </div>
    </footer>
  );
}
