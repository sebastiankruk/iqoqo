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

describe("ExtendedMetadata", () => {
  it("renders nothing when no relevant metadata is present", () => {
    const { container } = render(<ExtendedMetadata meta={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders categories when present", () => {
    render(<ExtendedMetadata meta={{ Categories: ["Sci-Fi", "Thriller"] }} />);
    expect(screen.getByText("Sci-Fi")).toBeInTheDocument();
    expect(screen.getByText("Thriller")).toBeInTheDocument();
  });

  it("renders description when present", () => {
    const desc = "This is a test description.";
    render(<ExtendedMetadata meta={{ Description: desc }} />);
    expect(screen.getByText(desc)).toBeInTheDocument();
  });

  it("renders additional details in a collapsible section", () => {
    const meta = {
      Publisher: "Test Publisher",
      Language: "English",
      // These keys should be hidden by default logic in the component
      Title: "Hidden Title",
      Year: "2023",
      cover_status: "ready",
    };

    render(<ExtendedMetadata meta={meta} />);

    // Initially hidden
    expect(screen.queryByText("Test Publisher")).not.toBeInTheDocument();

    // Expand
    const button = screen.getByText("Additional Details");
    fireEvent.click(button);

    // Now visible
    expect(screen.getByText("Test Publisher")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();

    // Hidden keys should remain hidden even when expanded
    expect(screen.queryByText("Hidden Title")).not.toBeInTheDocument();
  });

  it("renders primitives through expandable section", () => {
    const meta = {
      Publisher: "Test Publisher", // Hidden key, so must expand
    };
    render(<ExtendedMetadata meta={meta} />);
    const button = screen.getByText("Additional Details");
    fireEvent.click(button);
    expect(screen.getByText("Test Publisher")).toBeInTheDocument();
  });
});
