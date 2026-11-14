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

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { APP_VERSION } from "@/lib/version";
import { getSyncInstanceUrl } from "@/lib/capacitor/storage";
import { useTranslations } from "next-intl";

/**
 * Extract the host (including port if present) from a server URL or hostname string.
 *
 * @param {string} rawUrl - Raw URL or hostname
 * @returns {string} Extracted host string, or empty string if invalid
 */
function extractHost(rawUrl: string): string {
  const trimmed = rawUrl.trim();
  if (!trimmed) return "";
  try {
    const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    return new URL(withScheme).host;
  } catch {
    return trimmed.replace(/^https?:\/\//i, "").split("/")[0] || "";
  }
}

/** No-op subscription for static client-only host snapshot. */
const emptySubscribe = () => () => {};

/**
 * Resolve the connected server host for the current browser or Capacitor session.
 *
 * @returns {string} Connected server host
 */
function getConnectedHostSnapshot(): string {
  const configured = getSyncInstanceUrl() || process.env.NEXT_PUBLIC_INSTANCE_URL || "";
  if (configured) return extractHost(configured);
  return typeof window !== "undefined" ? window.location.host : "";
}

/**
 * Site footer displaying the iqoqo brand name, open-source sponsorship links,
 * connected server host, and the current UI version string.
 *
 * @returns {JSX.Element} The footer component
 */
export function Footer() {
  const t = useTranslations("Footer");
  const uiVersion = APP_VERSION;
  const serverHost = useSyncExternalStore(emptySubscribe, getConnectedHostSnapshot, () => "");

  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex flex-wrap items-center justify-between gap-2 px-6 py-5 max-w-7xl">
        <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-x-1.5">
          <span className="font-serif font-bold text-foreground">iqoqo</span> &middot; {t("libraryOfEverything")}{" "}
          &middot; {uiVersion}
          {serverHost && (
            <>
              <span>&middot;</span>
              <span
                data-testid="footer-connected-server"
                title={t("connectedServer", { host: serverHost })}
                className="inline-block max-w-[140px] sm:max-w-[240px] truncate align-bottom"
              >
                {t("connectedServer", { host: serverHost })}
              </span>
            </>
          )}{" "}
          &middot;{" "}
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
        <p className="text-xs text-muted-foreground flex items-center gap-3">
          <Link href="/help" className="hover:text-foreground underline transition-colors">
            Help
          </Link>
          &middot;
          <Link href="/federation/directory" className="hover:text-foreground underline transition-colors">
            Libraries
          </Link>
          &middot;
          <span>{t("rules")}</span>
        </p>
      </div>
    </footer>
  );
}
