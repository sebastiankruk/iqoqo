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

import { resolveMediaBadge, composeMediaBadgeLabel } from "@/lib/media-badge";

const EN_LABELS: Record<string, string> = {
  book: "Book",
  movie: "Movie",
  music: "Music",
  audiobook: "Audiobook",
  game: "Game",
  concert: "Concert",
};
const t = (key: string) => EN_LABELS[key] ?? key;

describe("resolveMediaBadge", () => {
  it("renders a vinyl record as Music / Vinyl (not CD / Audio)", () => {
    const badge = resolveMediaBadge("music", null, "vinyl");
    expect(badge.typeKey).toBe("music");
    expect(badge.formatLabel).toBe("Vinyl");
    expect(badge.kindKey).toBeUndefined();
    expect(badge.isAudio).toBe(true);
    expect(composeMediaBadgeLabel(badge, t)).toBe("Music / Vinyl");
  });

  it("renders a concert Blu-ray as Movie / Concert / Blu-ray", () => {
    const badge = resolveMediaBadge("video", "live_performance", "bluray");
    expect(badge.typeKey).toBe("movie");
    expect(badge.kindKey).toBe("concert");
    expect(badge.formatLabel).toBe("Blu-ray");
    expect(badge.isAudio).toBe(false);
    expect(composeMediaBadgeLabel(badge, t)).toBe("Movie / Concert / Blu-ray");
  });

  it("renders a CD album as Music / CD", () => {
    expect(composeMediaBadgeLabel(resolveMediaBadge("music", null, "cd"), t)).toBe("Music / CD");
  });

  it("renders a plain book without a redundant format segment", () => {
    const badge = resolveMediaBadge("text", null, "book");
    expect(badge.formatLabel).toBeUndefined();
    expect(composeMediaBadgeLabel(badge, t)).toBe("Book");
  });

  it("suppresses type-like junk in the format field (type-change fallout)", () => {
    const badge = resolveMediaBadge("video", "live_performance", "video");
    expect(badge.formatLabel).toBeUndefined();
    expect(composeMediaBadgeLabel(badge, t)).toBe("Movie / Concert");
  });

  it("suppresses unknown_* placeholders", () => {
    expect(resolveMediaBadge("movie", null, "unknown_video").formatLabel).toBeUndefined();
    expect(resolveMediaBadge("music", null, "unknown_audio").formatLabel).toBeUndefined();
  });

  it("collapses audiobook_cd into the Audiobook type segment", () => {
    const badge = resolveMediaBadge("audiobook", null, "audiobook_cd");
    expect(badge.formatLabel).toBeUndefined();
    expect(badge.isAudio).toBe(true);
    expect(composeMediaBadgeLabel(badge, t)).toBe("Audiobook");
  });

  it("keeps studio (kind=null) music without a kind segment", () => {
    expect(resolveMediaBadge("music", null, "sacd").kindKey).toBeUndefined();
  });

  it("renders a live music performance with kind and carrier", () => {
    expect(composeMediaBadgeLabel(resolveMediaBadge("music", "live_performance", "vinyl"), t)).toBe(
      "Music / Concert / Vinyl"
    );
  });

  it("falls back to the format category when content type is missing", () => {
    const badge = resolveMediaBadge(null, null, "bluray");
    expect(badge.typeKey).toBe("movie");
    expect(badge.formatLabel).toBe("Blu-ray");
  });

  it("defaults to book when nothing is known", () => {
    const badge = resolveMediaBadge(undefined, undefined, undefined);
    expect(badge.typeKey).toBe("book");
    expect(badge.formatLabel).toBeUndefined();
    expect(badge.isAudio).toBe(false);
  });

  it("maps game content types to the game segment", () => {
    expect(resolveMediaBadge("board_game", null, null).typeKey).toBe("game");
    expect(resolveMediaBadge("puzzle", null, null).typeKey).toBe("game");
  });

  it("normalizes case and whitespace", () => {
    const badge = resolveMediaBadge(" Music ", null, " Vinyl ");
    expect(composeMediaBadgeLabel(badge, t)).toBe("Music / Vinyl");
  });
});
