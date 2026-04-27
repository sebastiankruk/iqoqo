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
  // --- TEXT / BOOKS ---
  book: {
    label: "Book",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    icon: Book,
  },
  graphic_novel: {
    label: "Graphic Novel",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    parent: "book",
    icon: Book,
  },
  comic_book: {
    label: "Comic Book",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    parent: "book",
    icon: Book,
  },
  magazine: {
    label: "Magazine",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    parent: "book",
    icon: Book,
  },
  ebook: {
    label: "eBook",
    apiCategory: "text",
    aspectRatio: 2 / 3,
    parent: "book",
    icon: Book,
  },

  // --- AUDIOBOOKS (Category: audiobook) ---
  audiobook_cd: {
    label: "Audiobook CD",
    apiCategory: "audiobook",
    aspectRatio: 1 / 1,
    parent: "book", // Scanned under 'book' format in UI
    icon: Disc,
  },
  audiobook_cassette: {
    label: "Audiobook Cassette",
    apiCategory: "audiobook",
    aspectRatio: 1 / 1,
    parent: "book",
    icon: Disc,
  },
  audiobook_digital: {
    label: "Digital Audiobook",
    apiCategory: "audiobook",
    aspectRatio: 1 / 1,
    parent: "book",
    icon: Disc,
  },

  // --- MUSIC ---
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
  cassette: {
    label: "Cassette",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },
  minidisc: {
    label: "MiniDisc",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },
  cd_dvd_combo: {
    label: "CD + DVD",
    apiCategory: "music",
    aspectRatio: 1 / 1,
    parent: "music",
    icon: Disc,
  },

  // --- MOVIES ---
  movie: {
    label: "Video (DVD/Blu-Ray)",
    apiCategory: "movie",
    aspectRatio: 1 / 1,
    icon: Film,
  },
  dvd: {
    label: "DVD",
    apiCategory: "movie",
    aspectRatio: 1.5,
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
  "4k_uhd": {
    label: "4K Ultra HD",
    apiCategory: "movie",
    aspectRatio: 1.5,
    parent: "movie",
    icon: Film,
  },
  vcd: {
    label: "VCD",
    apiCategory: "movie",
    aspectRatio: 1 / 1,
    parent: "movie",
    icon: Film,
  },
  vhs: {
    label: "VHS",
    apiCategory: "movie",
    aspectRatio: 1.5,
    parent: "movie",
    icon: Film,
  },
  laserdisc: {
    label: "LaserDisc",
    apiCategory: "movie",
    aspectRatio: 1 / 1,
    parent: "movie",
    icon: Film,
  },

  // --- BOARD GAMES ---
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
  rpg_manual: {
    label: "RPG Manual",
    apiCategory: "board_game",
    aspectRatio: 2 / 3,
    parent: "board_game",
    icon: Book,
  },
  miniatures: {
    label: "Miniatures",
    apiCategory: "board_game",
    aspectRatio: 1 / 1,
    parent: "board_game",
    icon: Dices,
  },

  // --- PUZZLES ---
  puzzle: {
    label: "Puzzle",
    apiCategory: "puzzle",
    aspectRatio: 1 / 1,
    icon: Puzzle,
  },
  jigsaw_puzzle: {
    label: "Jigsaw Puzzle",
    apiCategory: "puzzle",
    aspectRatio: 1 / 1,
    parent: "puzzle",
    icon: Puzzle,
  },
  mechanical_puzzle: {
    label: "Mechanical Puzzle",
    apiCategory: "puzzle",
    aspectRatio: 1 / 1,
    parent: "puzzle",
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
