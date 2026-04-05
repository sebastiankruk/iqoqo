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
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExtendedMetadataVideo } from "@/components/item/extended-metadata-video";
import { ExtendedMetadataBoardGame } from "@/components/item/extended-metadata-boardgame";

describe("Video Metadata Display", () => {
  it("renders cast and runtime", () => {
    const meta = { cast: ["Actor 1"], runtime: 120, directors: ["Steven S."] };
    render(<ExtendedMetadataVideo meta={meta} />);
    expect(screen.getByText("120 min")).toBeInTheDocument();
    expect(screen.getByText("Actor 1")).toBeInTheDocument();
  });

  it("renders directors section", () => {
    const meta = { directors: ["Director One", "Director Two"] };
    render(<ExtendedMetadataVideo meta={meta} />);
    expect(screen.getByText("Director(s)")).toBeInTheDocument();
    expect(screen.getByText("Director One, Director Two")).toBeInTheDocument();
  });

  it("returns null when no video metadata is present", () => {
    const meta = {};
    const { container } = render(<ExtendedMetadataVideo meta={meta} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("handles Cast with capital C", () => {
    const meta = { Cast: ["Lead Actor"], Runtime: 90 };
    render(<ExtendedMetadataVideo meta={meta} />);
    expect(screen.getByText("90 min")).toBeInTheDocument();
  });
});

describe("BoardGame Metadata Display", () => {
  it("renders player counts and mechanics", () => {
    const meta = { min_players: 2, max_players: 4, playing_time: 45, mechanics: ["Deckbuilding"] };
    render(<ExtendedMetadataBoardGame meta={meta} />);
    expect(screen.getByText("2 - 4")).toBeInTheDocument();
    expect(screen.getByText("Deckbuilding")).toBeInTheDocument();
  });

  it("renders same player count when min equals max", () => {
    const meta = { min_players: 4, max_players: 4 };
    render(<ExtendedMetadataBoardGame meta={meta} />);
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders playtime", () => {
    const meta = { playing_time: 60 };
    render(<ExtendedMetadataBoardGame meta={meta} />);
    expect(screen.getByText("60 min")).toBeInTheDocument();
  });

  it("returns null when no boardgame metadata is present", () => {
    const meta = {};
    const { container } = render(<ExtendedMetadataBoardGame meta={meta} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("handles MinPlayers with capital M", () => {
    const meta = { MinPlayers: 2, MaxPlayers: 6, PlayTime: 30 };
    render(<ExtendedMetadataBoardGame meta={meta} />);
    expect(screen.getByText("2 - 6")).toBeInTheDocument();
    expect(screen.getByText("30 min")).toBeInTheDocument();
  });
});
