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
import { Braces, Rss } from "lucide-react";
import { openExternalUrl } from "@/lib/capacitor/navigation";
import { isNativeApp } from "@/lib/capacitor/platform";
import { resolvePublicUrl } from "@/lib/utils";

interface PublicFeedButtonProps {
  feedPath: string;
  label?: string;
  className?: string;
  title?: string;
  variant?: "rss" | "jsonld";
}

/**
 * Client-side RSS or JSON-LD feed link button. On native mobile (Capacitor), opens
 * via the system browser instead of the internal WebView.
 */
export function PublicFeedButton({
  feedPath,
  label = "RSS Feed",
  className = "inline-flex items-center gap-2 rounded-lg border bg-background px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground shadow-sm transition-all",
  title = "Subscribe to RSS feed",
  variant = "rss",
}: PublicFeedButtonProps) {
  const url = isNativeApp() ? resolvePublicUrl(feedPath) : feedPath;

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (isNativeApp()) {
      e.preventDefault();
      openExternalUrl(resolvePublicUrl(feedPath));
    }
  };

  return (
    <a href={url} target="_blank" rel="noopener noreferrer" onClick={handleClick} className={className} title={title}>
      {variant === "jsonld" ? <Braces className="h-4 w-4 text-primary" /> : <Rss className="h-4 w-4 text-orange-500" />}
      <span>{label}</span>
    </a>
  );
}
