// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

import { Book, Disc, Film, Dices, Puzzle, LucideIcon } from "lucide-react";
import { MediaFormat, ScanFormat } from "@/types/frbr";

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

/**
 * Central registry of all supported media formats and their UI/API properties.
 * This is the SINGLE SOURCE OF TRUTH for media-related UI logic.
 */
export const MEDIA_REGISTRY: Record<MediaFormat | ScanFormat, MediaMetadata> = {
  book: {
    label: "Book",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    icon: Book,
  },
  audio: {
    label: "Audio (CD/Vinyl)",
    apiCategory: "sound",
    aspectRatio: 1 / 1,
    icon: Disc,
  },
  cd: {
    label: "CD",
    apiCategory: "sound",
    aspectRatio: 1 / 1,
    parent: "audio",
    icon: Disc,
  },
  vinyl: {
    label: "Vinyl",
    apiCategory: "sound",
    aspectRatio: 1 / 1,
    parent: "audio",
    icon: Disc,
  },
  video: {
    label: "Video (DVD/Blu-Ray)",
    apiCategory: "moving image",
    aspectRatio: 1 / 1,
    icon: Film,
  },
  boardgame: {
    label: "Board Game",
    apiCategory: "boardgame",
    aspectRatio: 1 / 1,
    icon: Dices,
  },
  puzzle: {
    label: "Jigsaw Puzzle",
    apiCategory: "three-dimensional object",
    aspectRatio: 1 / 1,
    icon: Puzzle,
  },
};

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
