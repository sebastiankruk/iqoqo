// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

import { Book, Disc, Film, Dices, Puzzle, LucideIcon } from "lucide-react";
import { MEDIA_HIERARCHY, MediaFormat, ScanFormat, MediaCategory, SCAN_FORMATS } from "@/types/taxonomy";

/**
 * Metadata for a specific media format or category.
 */
export interface MediaMetadata {
  /** User-friendly label for the format */
  label: string;
  /** High-level API content_type mapping */
  apiCategory: string;
  /** Aspect ratio for the scanner viewfinder (width/height) */
  aspectRatio: number;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Optional parent category for sub-formats (e.g., 'cd' -> 'audio') */
  parent?: ScanFormat;
}

const ICONS: Record<string, LucideIcon> = {
  Book,
  Disc,
  Film,
  Dices,
  Puzzle,
};

/**
 * Builds the MEDIA_REGISTRY dynamically from the auto-generated MEDIA_HIERARCHY.
 *
 * @returns The built media registry
 */
function buildMediaRegistry(): Record<MediaFormat | ScanFormat, MediaMetadata> {
  const registry = {} as Record<string, MediaMetadata>;

  // Iterate over all categories in the hierarchy
  Object.entries(MEDIA_HIERARCHY).forEach(([catId, info]) => {
    const category = catId as MediaCategory;

    // Use UI properties from taxonomy if they exist
    const iconName = "ui_icon" in info && info.ui_icon ? String(info.ui_icon) : "Book";
    const icon = ICONS[iconName] || Book;
    const catAspectRatio =
      "ui_aspect_ratio" in info && info.ui_aspect_ratio !== null ? Number(info.ui_aspect_ratio) : 1;
    const catParent = "ui_parent" in info && info.ui_parent !== null ? String(info.ui_parent) : undefined;

    // Some categories map to a different scan format ID (e.g., 'text' -> 'book')
    const scanFormatId = (category as string) === "text" ? "book" : (category as string);

    // Add the scan category entry if it's in SCAN_FORMATS
    if ((SCAN_FORMATS as readonly string[]).includes(scanFormatId)) {
      registry[scanFormatId] = {
        label: info.label,
        apiCategory: category,
        icon,
        aspectRatio: catAspectRatio,
      };
    }

    // Add all specific formats belonging to this category
    interface TaxonomyFormat {
      id: string;
      label: string;
      ui_aspect_ratio?: number | null;
      ui_parent?: string | null;
    }

    (info.formats as readonly TaxonomyFormat[]).forEach(fmt => {
      const fmtAspectRatio =
        "ui_aspect_ratio" in fmt && fmt.ui_aspect_ratio !== null ? Number(fmt.ui_aspect_ratio) : catAspectRatio;
      const fmtParent =
        "ui_parent" in fmt && fmt.ui_parent !== null ? String(fmt.ui_parent) : catParent || scanFormatId;

      registry[fmt.id] = {
        label: fmt.label,
        apiCategory: category,
        icon,
        aspectRatio: fmtAspectRatio,
        parent: fmtParent as ScanFormat,
      };
    });
  });

  return registry as Record<MediaFormat | ScanFormat, MediaMetadata>;
}

/**
 * Central registry of all supported media formats and their UI/API properties.
 * This is the SINGLE SOURCE OF TRUTH for media-related UI logic,
 * derived from shared/taxonomy.yaml.
 */
export const MEDIA_REGISTRY: Record<MediaFormat | ScanFormat, MediaMetadata> = buildMediaRegistry();

/**
 * Returns the metadata for a given format, falling back to 'book' if not found.
 *
 * @param format - The media format to lookup
 * @returns The metadata for the format
 */
export function getMediaMetadata(format: string): MediaMetadata {
  return MEDIA_REGISTRY[format as MediaFormat] || MEDIA_REGISTRY.book;
}

/**
 * Maps a UI format string to its corresponding backend API content_type.
 *
 * @param format - The UI format string
 * @returns The backend API category
 */
export function mapFormatToApi(format: string): string {
  return getMediaMetadata(format).apiCategory;
}
