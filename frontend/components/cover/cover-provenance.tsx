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

import * as React from "react";
import { Camera, Globe, Store, Download, Disc, Film, Gamepad2, Sparkles, ImageOff, HelpCircle } from "lucide-react";
import { useTranslations } from "next-intl";

interface CoverProvenanceProps {
  source?: string | null;
  className?: string;
  showPrefix?: boolean;
}

/**
 * Renders a small badge showing cover provenance source and label with an icon.
 *
 * @param props - Component props
 * @param props.source - Cover source identifier string
 * @param props.className - Additional CSS classes
 * @param props.showPrefix - Whether to display "Source:" prefix
 * @returns Component JSX
 */
export function CoverProvenance({ source, className = "", showPrefix = true }: CoverProvenanceProps) {
  const t = useTranslations("CoverProvenance");

  if (!source) {
    return (
      <div
        data-testid="cover-provenance"
        className={`inline-flex items-center gap-1.5 rounded-full bg-secondary/80 px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground ring-1 ring-border ${className}`}
      >
        <HelpCircle className="h-3 w-3 text-muted-foreground/70" />
        <span>{showPrefix ? `${t("sourcePrefix")}: ${t("unknown")}` : t("unknown")}</span>
      </div>
    );
  }

  let labelKey = "unknown";
  let Icon = HelpCircle;

  if (source === "user_photo") {
    labelKey = "user_photo";
    Icon = Camera;
  } else if (source === "api_openlibrary") {
    labelKey = "api_openlibrary";
    Icon = Globe;
  } else if (source === "api_google_books") {
    labelKey = "api_google_books";
    Icon = Globe;
  } else if (source === "api_allegro") {
    labelKey = "api_allegro";
    Icon = Store;
  } else if (source === "api_direct_download") {
    labelKey = "api_direct_download";
    Icon = Download;
  } else if (source === "api_musicbrainz") {
    labelKey = "api_musicbrainz";
    Icon = Disc;
  } else if (source === "api_tmdb") {
    labelKey = "api_tmdb";
    Icon = Film;
  } else if (source === "api_igdb") {
    labelKey = "api_igdb";
    Icon = Gamepad2;
  } else if (source.startsWith("llm_")) {
    labelKey = "ai_generated";
    Icon = Sparkles;
  } else if (source === "fallback_pil") {
    labelKey = "fallback_pil";
    Icon = ImageOff;
  }

  const label = t(labelKey);

  return (
    <div
      data-testid="cover-provenance"
      className={`inline-flex items-center gap-1.5 rounded-full bg-secondary/80 px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground ring-1 ring-border ${className}`}
    >
      <Icon className="h-3 w-3 text-muted-foreground/70" />
      <span>{showPrefix ? `${t("sourcePrefix")}: ${label}` : label}</span>
    </div>
  );
}
