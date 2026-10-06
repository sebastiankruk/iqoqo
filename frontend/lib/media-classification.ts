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

/**
 * Shared medium classification for UI components.
 *
 * Before this existed, the same "is this a video?" test was written out in
 * eight different spellings across six components, and the lists had already
 * drifted: `extended-metadata.tsx` counted `movie` and `unknown_video` as
 * video while the other four did not, and counted `cards` as a board game
 * while the others did not. The same Item therefore rendered a Film icon in
 * one component and a book badge in another.
 *
 * These are the canonical lists. When a format needs adding, add it here
 * rather than at a call site -- that divergence is the defect this module
 * exists to remove.
 */

/** Manifestation carrier formats that mean the work is moving image. */
const VIDEO_FORMATS: ReadonlySet<string> = new Set([
  "dvd",
  "bluray",
  "video",
  "movie",
  "moving image",
  "unknown_video",
]);

/** Manifestation carrier formats that mean the work is a board game. */
const BOARD_GAME_FORMATS: ReadonlySet<string> = new Set([
  "boardgame",
  "board_game",
  "cards",
  "three-dimensional object",
]);

/** Formats that mean the work is a puzzle specifically. */
const PUZZLE_FORMATS: ReadonlySet<string> = new Set(["puzzle", "jigsaw", "jigsaw puzzle"]);

/** Formats that mean the work is audio. */
const AUDIO_FORMATS: ReadonlySet<string> = new Set([
  "audio",
  "cd",
  "vinyl",
  "lp",
  "ep",
  "45",
  "audiobook",
  "cd-ep",
  "sacd",
  "bluray_audio",
  "audiobook_cd",
  "unknown_audio",
]);

/**
 * Normalise a possibly-absent format string for set membership.
 *
 * @param value - Raw format string, possibly nullish or differently cased.
 * @returns The trimmed lowercase form, or an empty string when absent.
 */
function norm(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

/**
 * Whether the given formats describe a moving-image work.
 *
 * @param values - Candidate format strings, e.g. the Manifestation `format` and a fallback carrier.
 * @returns True when any candidate is a video format.
 */
export function isVideoFormat(...values: (string | null | undefined)[]): boolean {
  return values.some(v => VIDEO_FORMATS.has(norm(v)));
}

/**
 * Whether the given formats describe a board game.
 *
 * @param values - Candidate format strings.
 * @returns True when any candidate is a board-game format.
 */
export function isBoardGameFormat(...values: (string | null | undefined)[]): boolean {
  return values.some(v => BOARD_GAME_FORMATS.has(norm(v)));
}

/**
 * Whether the given formats describe a puzzle specifically.
 *
 * @param values - Candidate format strings.
 * @returns True when any candidate is a puzzle format.
 */
export function isPuzzleFormat(...values: (string | null | undefined)[]): boolean {
  return values.some(v => PUZZLE_FORMATS.has(norm(v)));
}

/**
 * Whether the given formats describe an audio work.
 *
 * @param values - Candidate format strings.
 * @returns True when any candidate is an audio format.
 */
export function isAudioFormat(...values: (string | null | undefined)[]): boolean {
  return values.some(v => AUDIO_FORMATS.has(norm(v)));
}
