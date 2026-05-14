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
import { Share2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

interface ShareButtonProps {
  /** The URL to share. Defaults to current window location if omitted. */
  url?: string;
  /** Optional title for the share dialog */
  title?: string;
  /** Optional text for the share dialog */
  text?: string;
}

/**
 * Share button that uses the Web Share API when available,
 * falling back to clipboard copy.
 * @param root0 - The component props.
 * @param root0.url - The URL to share. Defaults to current window location if omitted.
 * @param root0.title - Optional title for the share dialog.
 * @param root0.text - Optional text for the share dialog.
 * @returns The rendered share button.
 */
export function ShareButton({ url, title, text }: ShareButtonProps) {
  const t = useTranslations("Common");
  const [copied, setCopied] = React.useState(false);

  const handleShare = async () => {
    const shareUrl = url || (typeof window !== "undefined" ? window.location.href : "");
    if (!shareUrl) return;

    // Attempt Web Share API first
    if (navigator.share) {
      try {
        await navigator.share({
          title: title || document.title,
          text: text,
          url: shareUrl,
        });
        return;
      } catch (err) {
        // user cancelled or share failed, proceed to clipboard if not a cancellation
        if (err instanceof Error && err.name === "AbortError") return;
        console.error("Share failed", err);
      }
    }

    // Fallback to clipboard
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Link copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Could not copy link");
      console.error("Clipboard failed", err);
    }
  };

  return (
    <Button onClick={handleShare} variant="outline" size="sm" className="flex items-center gap-2 transition-all">
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Share2 className="w-4 h-4" />}
      <span>{copied ? "Copied!" : t("share")}</span>
    </Button>
  );
}
