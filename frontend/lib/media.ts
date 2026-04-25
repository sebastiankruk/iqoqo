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
  audiobook_cd: {
    label: "Audiobook CD",
    apiCategory: "text",
    aspectRatio: 1 / 1,
    parent: "book",
    icon: Disc,
  },
  music: {
    label: "Music (CD/Vinyl)",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    icon: Disc,
  },
  cd: {
    label: "CD",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },
  vinyl: {
    label: "Vinyl",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },
  sacd: {
    label: "SACD",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },
  movie: {
    label: "Video (DVD/Blu-Ray)",
    apiCategory: "movie",
    aspectRatio: 1 / 1,
    icon: Film,
  },
  dvd: {
    label: "DVD",
    apiCategory: "movie",
    aspectRatio: 1.5, // 3:2 approximately for DVD cases or just 1:1 for discs
    parent: "movie",
    icon: Film,
  },
  bluray: {
    label: "Blu-Ray",
    apiCategory: "movie",
    aspectRatio: 1.5,
    parent: "movie",
    icon: Film,
  },
  board_game: {
    label: "Board Game",
    apiCategory: "board_game",
    aspectRatio: 1 / 1,
    icon: Dices,
  },
  cards: {
    label: "Cards",
    apiCategory: "board_game",
    aspectRatio: 1 / 1,
    parent: "board_game",
    icon: Dices,
  },
  puzzle: {
    label: "Jigsaw Puzzle",
    apiCategory: "puzzle",
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
