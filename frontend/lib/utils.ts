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
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names.
 *
 * @param inputs - Class names to merge
 * @returns {string} Merged class names
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Checks if a given media format string represents an audio-based manifestation.
 *
 * @param format - The format string to check (e.g., "CD", "Vinyl", "Audiobook")
 * @returns {boolean} True if the format is audio-based
 */
export function isAudioMedia(format: string | undefined): boolean {
  if (!format) return false;
  const audioFormats = new Set(["audio", "cd", "vinyl", "lp", "ep", "45", "audiobook", "cd-ep", "sacd"]);
  return audioFormats.has(format.toLowerCase());
}

