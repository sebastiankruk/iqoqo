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

import { useEffect, useState } from "react";
import Image from "next/image";
import { X, Images } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { useManifestationImages } from "@/lib/api/hooks/catalog";
import { resolveApiUrl } from "@/lib/utils";

export interface ManifestationCoversGalleryProps {
  manifestationId: number;
  primaryCoverUrl?: string | null;
}

/**
 * Displays community-contributed covers and supplementary scans attached to a Manifestation (F3).
 */
export function ManifestationCoversGallery({ manifestationId, primaryCoverUrl }: ManifestationCoversGalleryProps) {
  const t = useTranslations("Manifestation");
  const { data: images = [] } = useManifestationImages(manifestationId);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!previewUrl) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPreviewUrl(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [previewUrl]);

  const normalizedPrimary = primaryCoverUrl?.trim() || "";
  const galleryImages = images.filter(img => {
    const resolved = resolveApiUrl(img.url) || img.url;
    return Boolean(resolved) && resolved !== normalizedPrimary && img.url !== normalizedPrimary;
  });

  if (galleryImages.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2" data-testid="manifestation-covers-gallery">
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <Images className="h-3.5 w-3.5" />
        <span>{t("contributedCovers")}</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {galleryImages.map(img => {
          const src = resolveApiUrl(img.url) || img.url;
          return (
            <button
              key={img.id}
              type="button"
              onClick={() => setPreviewUrl(src)}
              className="group relative aspect-[2/3] overflow-hidden rounded-lg border border-border bg-muted text-left focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <Image src={src} alt={img.label || t("contributedCovers")} fill unoptimized className="object-cover" />
              <Badge
                variant="secondary"
                className="absolute bottom-1 left-1 right-1 truncate text-[10px] px-1 py-0 bg-background/85 backdrop-blur-sm"
              >
                {img.source || img.label}
              </Badge>
            </button>
          );
        })}
      </div>

      {previewUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setPreviewUrl(null)}
          role="dialog"
          aria-modal="true"
        >
          <div className="relative max-h-[85vh] max-w-2xl w-full aspect-[2/3]" onClick={e => e.stopPropagation()}>
            <button
              type="button"
              aria-label={t("closePreview")}
              onClick={() => setPreviewUrl(null)}
              className="absolute -top-10 right-0 rounded-full bg-background/90 p-1.5 text-foreground hover:bg-background"
            >
              <X className="h-5 w-5" />
            </button>
            <Image
              src={previewUrl}
              alt={t("contributedCovers")}
              fill
              unoptimized
              className="object-contain rounded-lg"
            />
          </div>
        </div>
      )}
    </div>
  );
}
