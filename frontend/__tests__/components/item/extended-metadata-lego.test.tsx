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

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExtendedMetadataLego } from "@/components/item/extended-metadata-lego";

describe("ExtendedMetadataLego", () => {
  it("renders LEGO set details, pieces, minifigs, and physical state", () => {
    const meta = {
      set_number: "10318-1",
      piece_count: 2083,
      minifig_count: 0,
      theme: "Icons",
      build_status: "built",
      instructions_included: true,
      missing_pieces_count: 2,
      external_url: "https://rebrickable.com/sets/10318-1/",
    };

    render(<ExtendedMetadataLego meta={meta} />);

    expect(screen.getByText("LEGO Set Details")).toBeInTheDocument();
    expect(screen.getByTestId("lego-set-number")).toHaveTextContent("10318-1");
    expect(screen.getByTestId("lego-piece-count")).toHaveTextContent("2083 Pieces");
    expect(screen.getByTestId("lego-minifig-count")).toHaveTextContent("0");
    expect(screen.getByText("Built")).toBeInTheDocument();
    expect(screen.getByText("Included")).toBeInTheDocument();
    expect(screen.getByText("Missing: 2 pieces")).toBeInTheDocument();
    expect(screen.getByText("View on Rebrickable")).toBeInTheDocument();
  });
});
