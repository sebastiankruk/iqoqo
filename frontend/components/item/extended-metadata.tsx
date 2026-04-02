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

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { isAudioMedia } from "@/lib/utils";

/** Props for ExtendedMetadata component */
interface ExtendedMetadataProps {
  meta: Record<string, unknown>;
}

/**
 * Extended metadata component.
 *
 * @param root0 - The props object
 * @param root0.meta - The metadata to display
 * @returns {JSX.Element | null} The component or null if no metadata
 */
export function ExtendedMetadata({ meta }: ExtendedMetadataProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const description = meta["Description"] as string | undefined;
  const categories = (meta["Categories"] as string[] | undefined) ?? [];

  // Audio specific metadata
  const format = meta["format"] as string | undefined;
  const isAudio = isAudioMedia(format);
  const trackList = meta["track_list"] as Array<{ position: string; title: string; duration_seconds: number }> | undefined;

  // Filter out internal keys and keys already displayed elsewhere
  const hiddenKeys = new Set([
    "Title",
    "Authors",
    "Description",
    "Categories",
    "cover_status",
    "cover_source",
    "cover_url",
    "local_cover",
    "tags",
    "Year",
    "Pages",
    "Subtitle",
    "track_list",
    "additional_images",
    "format",
    "label",
    "catalog_number",
    "matrix_number",
    "pressing_number",
    "disc_count",
  ]);
  const extraKeys = Object.keys(meta).filter(k => !hiddenKeys.has(k) && typeof meta[k] !== "object");

  if (!description && categories.length === 0 && !isAudio && !trackList && extraKeys.length === 0) return null;

  return (
    <div className="space-y-4 py-4">
      {/* Always Visible: Categories */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {categories.map(cat => (
            <Badge key={cat} variant="secondary">
              {cat}
            </Badge>
          ))}
        </div>
      )}

      {/* Always Visible: Description */}
      {description && (
        <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
          <p>{description}</p>
        </div>
      )}

      {/* Audio Specific Details */}
      {isAudio && (
        <div className="rounded-lg border bg-card/50 p-4 shadow-sm">
          <h3 className="font-semibold text-lg mb-4 text-foreground">Release Information</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            {Boolean(meta["label"]) && (
              <div className="flex flex-col">
                <span className="text-muted-foreground">Label</span>
                <span className="font-medium">{meta["label"] as string}</span>
              </div>
            )}
            {Boolean(meta["catalog_number"]) && (
              <div className="flex flex-col">
                <span className="text-muted-foreground">Catalog #</span>
                <span className="font-medium">{meta["catalog_number"] as string}</span>
              </div>
            )}
            {Boolean(meta["matrix_number"]) && (
              <div className="flex flex-col">
                <span className="text-muted-foreground">Matrix #</span>
                <span className="font-medium">{meta["matrix_number"] as string}</span>
              </div>
            )}
            {Boolean(meta["disc_count"]) && (
              <div className="flex flex-col">
                <span className="text-muted-foreground">Discs</span>
                <span className="font-medium">{meta["disc_count"] as number}</span>
              </div>
            )}
            {format && (
              <div className="flex flex-col">
                <span className="text-muted-foreground">Format</span>
                <span className="font-medium">{format}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tracklist Table */}
      {trackList && trackList.length > 0 && (
        <div className="rounded-lg border bg-card/50 p-4 shadow-sm">
          <h3 className="font-semibold text-lg mb-4 text-foreground">Tracklist</h3>
          <div className="divide-y border-t border-muted">
            {trackList.map(track => (
              <div key={track.position} className="py-2 flex justify-between text-sm items-center hover:bg-muted/30 px-2 rounded-sm transition-colors">
                <div className="flex gap-4">
                  <span className="text-muted-foreground w-8 font-mono">{track.position}</span>
                  <span className="font-medium">{track.title}</span>
                </div>
                <span className="text-muted-foreground font-mono">
                  {Math.floor(track.duration_seconds / 60)}:{(track.duration_seconds % 60).toString().padStart(2, "0")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsible: Raw Metadata */}
      {extraKeys.length > 0 && (
        <div className="border rounded-lg p-4 bg-muted/30">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span className="font-semibold">Additional Details</span>
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>

          {isExpanded && (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 mt-4 text-sm">
              {extraKeys.map(key => (
                <div key={key} className="flex flex-col">
                  <dt className="font-medium text-foreground">{key}</dt>
                  <dd className="text-muted-foreground break-words">{String(meta[key])}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </div>
  );
}
