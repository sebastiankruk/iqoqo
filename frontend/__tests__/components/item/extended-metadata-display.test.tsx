// @vitest-environment jsdom
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
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExtendedMetadata } from "@/components/item/extended-metadata";
import { FIELD_CHAINS } from "@/lib/meta";

describe("ExtendedMetadata Display Projection & Duplication Tests", () => {
  it("task 0.1: asserts that with meta={{ Format: 'Vinyl' }} value appears exactly once when Additional Details expanded", () => {
    render(<ExtendedMetadata meta={{ Format: "Vinyl" }} />);
    const button = screen.queryByRole("button", { name: /additional details/i });
    if (button) {
      fireEvent.click(button);
    }

    // "VINYL" appears in Media Format section, check all occurrences of "Vinyl" (case-insensitive)
    const matches = screen.getAllByText(/vinyl/i);
    expect(matches).toHaveLength(1);
  });

  it("task 0.2: capitalised Format, Author, Publisher fail / lowercase pass asymmetry test", () => {
    // Lowercase format: should appear exactly once in Media Format, suppressed from Additional Details
    const { unmount: unmount1 } = render(<ExtendedMetadata meta={{ format: "vinyl" }} />);
    expect(screen.queryByRole("button", { name: /additional details/i })).not.toBeInTheDocument();
    expect(screen.getAllByText(/vinyl/i)).toHaveLength(1);
    unmount1();

    // Lowercase author: should not appear in additional details if hiddenKeys suppresses it
    const { unmount: unmount2 } = render(<ExtendedMetadata meta={{ author: "Stanislaw Lem" }} />);
    expect(screen.queryByText(/stanislaw lem/i)).not.toBeInTheDocument();
    unmount2();

    // Capitalised Author:
    // Before fix, Author was not suppressed so it leaked into Additional Details.
    // With isKnownMetaSpelling, it is suppressed so it does not leak.
    const { unmount: unmount3 } = render(<ExtendedMetadata meta={{ Author: "Stanislaw Lem" }} />);
    expect(screen.queryByText(/stanislaw lem/i)).not.toBeInTheDocument();
    unmount3();

    // Lowercase publisher:
    const { unmount: unmount4 } = render(<ExtendedMetadata meta={{ format: "vinyl", publisher: "Blue Note" }} />);
    expect(screen.queryByRole("button", { name: /additional details/i })).not.toBeInTheDocument();
    expect(screen.getAllByText(/blue note/i)).toHaveLength(1);
    unmount4();

    // Capitalised Publisher:
    render(<ExtendedMetadata meta={{ format: "vinyl", Publisher: "Blue Note" }} />);
    const btnAudioPub = screen.queryByRole("button", { name: /additional details/i });
    if (btnAudioPub) {
      fireEvent.click(btnAudioPub);
    }
    expect(screen.getAllByText(/blue note/i)).toHaveLength(1);
  });

  it("task 1.3: asserts that adding a spelling to FIELD_CHAINS alone keeps the field rendering once", () => {
    // Dynamically extend FIELD_CHAINS.format with a temporary custom spelling
    const chains = FIELD_CHAINS as unknown as { format: string[] };
    const original = [...chains.format];
    try {
      chains.format.push("format_custom_alt");

      render(<ExtendedMetadata meta={{ format_custom_alt: "Vinyl" }} />);
      const button = screen.queryByRole("button", { name: /additional details/i });
      if (button) {
        fireEvent.click(button);
      }

      // "VINYL" appears in Media Format, suppressed from Additional Details, so exactly 1
      const matches = screen.getAllByText(/vinyl/i);
      expect(matches).toHaveLength(1);
    } finally {
      chains.format = original;
    }
  });

  it("task 3.1: renders Additional Details directly from display.additional_details when provided", () => {
    const meta = { Format: "Vinyl", CustomField: "IgnoredInMeta" };
    const display = {
      sections: { format: "Vinyl" },
      additional_details: [{ key: "custom_key", label: "Projected Custom Label", value: "Projected Custom Value" }],
    };

    render(<ExtendedMetadata meta={meta} display={display} />);
    const button = screen.getByRole("button", { name: /additional details/i });
    fireEvent.click(button);

    expect(screen.getByText("Projected Custom Label")).toBeInTheDocument();
    expect(screen.getByText("Projected Custom Value")).toBeInTheDocument();
    // The raw meta key not in display projection should not be rendered
    expect(screen.queryByText("IgnoredInMeta")).not.toBeInTheDocument();
  });
});
