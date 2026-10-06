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
import { describe, it, expect } from "vitest";
import { isAudioFormat, isBoardGameFormat, isPuzzleFormat, isVideoFormat } from "@/lib/media-classification";

describe("media classification", () => {
  it("classifies moving-image carriers", () => {
    for (const f of ["dvd", "bluray", "video", "movie", "moving image", "unknown_video"]) {
      expect(isVideoFormat(f), f).toBe(true);
    }
    expect(isVideoFormat("book")).toBe(false);
    expect(isVideoFormat("cd")).toBe(false);
  });

  it("classifies board-game carriers", () => {
    for (const f of ["boardgame", "board_game", "cards", "three-dimensional object"]) {
      expect(isBoardGameFormat(f), f).toBe(true);
    }
    expect(isBoardGameFormat("book")).toBe(false);
  });

  it("classifies puzzles separately from board games", () => {
    for (const f of ["puzzle", "jigsaw", "jigsaw puzzle"]) {
      expect(isPuzzleFormat(f), f).toBe(true);
    }
    expect(isPuzzleFormat("boardgame")).toBe(false);
  });

  it("classifies audio carriers", () => {
    for (const f of ["cd", "vinyl", "lp", "audiobook", "sacd", "unknown_audio"]) {
      expect(isAudioFormat(f), f).toBe(true);
    }
    expect(isAudioFormat("dvd")).toBe(false);
  });

  it("is case-insensitive and tolerates surrounding whitespace", () => {
    expect(isVideoFormat("  DVD  ")).toBe(true);
    expect(isBoardGameFormat("BoardGame")).toBe(true);
  });

  it("treats absent values as non-matching rather than throwing", () => {
    expect(isVideoFormat(undefined)).toBe(false);
    expect(isVideoFormat(null)).toBe(false);
    expect(isVideoFormat("")).toBe(false);
  });

  // The regression these pin: the lists had already drifted between call
  // sites. extended-metadata counted "movie", "unknown_video" and "cards"
  // while the other five components did not, so the same Item rendered a Film
  // icon in one place and a book badge in another.
  it("uses one canonical list, so every component agrees", () => {
    expect(isVideoFormat("movie")).toBe(true);
    expect(isVideoFormat("unknown_video")).toBe(true);
    expect(isBoardGameFormat("cards")).toBe(true);
  });

  it("accepts several candidates and matches if any qualifies", () => {
    // wishlist-card classified against `format || rawContentType`.
    expect(isVideoFormat(undefined, "dvd")).toBe(true);
    expect(isBoardGameFormat("", "boardgame")).toBe(true);
    expect(isPuzzleFormat(undefined, undefined, "jigsaw")).toBe(true);
  });
});
