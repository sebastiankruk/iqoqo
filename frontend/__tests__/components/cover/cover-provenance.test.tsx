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
import { describe, it, expect, vi } from "vitest";
import { CoverProvenance } from "@/components/cover/cover-provenance";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      sourcePrefix: "Source",
      user_photo: "User photo",
      api_openlibrary: "OpenLibrary",
      api_google_books: "Google Books",
      api_allegro: "Allegro",
      api_direct_download: "Direct download",
      api_musicbrainz: "MusicBrainz",
      api_tmdb: "TMDb",
      api_igdb: "IGDB",
      ai_generated: "AI-generated",
      fallback_pil: "Placeholder",
      unknown: "Unknown",
    };
    return map[key] || key;
  },
}));

describe("CoverProvenance", () => {
  it("renders correct label for OpenLibrary source", () => {
    render(<CoverProvenance source="api_openlibrary" />);
    expect(screen.getByTestId("cover-provenance")).toHaveTextContent("Source: OpenLibrary");
  });

  it("renders correct label for AI generated source", () => {
    render(<CoverProvenance source="llm_gemini" />);
    expect(screen.getByTestId("cover-provenance")).toHaveTextContent("Source: AI-generated");
  });

  it("renders correct label for PIL fallback placeholder", () => {
    render(<CoverProvenance source="fallback_pil" />);
    expect(screen.getByTestId("cover-provenance")).toHaveTextContent("Source: Placeholder");
  });

  it("renders correct label for MusicBrainz source", () => {
    render(<CoverProvenance source="api_musicbrainz" />);
    expect(screen.getByTestId("cover-provenance")).toHaveTextContent("Source: MusicBrainz");
  });

  it("renders fallback for missing or unknown source", () => {
    render(<CoverProvenance source={null} />);
    expect(screen.getByTestId("cover-provenance")).toHaveTextContent("Source: Unknown");
  });
});
