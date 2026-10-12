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
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { TagCloud } from "@/components/ui/tag-cloud";

describe("TagCloud component", () => {
  it("renders empty when tags list is empty", () => {
    const { container } = render(<TagCloud tags={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders all tags when count is under maxInitial threshold", () => {
    const tags = ["Post-Punk", "New Wave", "Gothic Rock"];
    render(<TagCloud tags={tags} maxInitial={5} />);

    expect(screen.getByText("Post-Punk")).toBeInTheDocument();
    expect(screen.getByText("New Wave")).toBeInTheDocument();
    expect(screen.getByText("Gothic Rock")).toBeInTheDocument();
    expect(screen.queryByTestId("tag-cloud-toggle")).toBeNull();
  });

  it("folds tags and toggles expansion on click when count exceeds maxInitial", async () => {
    const user = userEvent.setup();
    const tags = Array.from({ length: 15 }, (_, i) => `Tag-${i + 1}`);

    render(<TagCloud tags={tags} maxInitial={10} />);

    // Top 10 tags should be visible
    expect(screen.getByText("Tag-1")).toBeInTheDocument();
    expect(screen.getByText("Tag-10")).toBeInTheDocument();
    // 11th tag should be folded initially
    expect(screen.queryByText("Tag-11")).toBeNull();

    // Toggle button displays "+5 more"
    const toggle = screen.getByTestId("tag-cloud-toggle");
    expect(toggle).toHaveTextContent("+5 more");

    // Click toggle to expand
    await user.click(toggle);
    expect(screen.getByText("Tag-11")).toBeInTheDocument();
    expect(screen.getByText("Tag-15")).toBeInTheDocument();
    expect(toggle).toHaveTextContent("Show less");

    // Click toggle to collapse
    await user.click(toggle);
    expect(screen.queryByText("Tag-11")).toBeNull();
    expect(toggle).toHaveTextContent("+5 more");
  });

  it("renders provenance tooltip titles accurately", () => {
    const tags = [
      { name: "Electronic", source: "discogs:style" },
      { name: "Fiction", source: "openlibrary:subject" },
      { name: "Favorites", source: "user:curation" },
      { name: "Generic" },
    ];

    render(<TagCloud tags={tags} />);

    const chip1 = screen.getByText("Electronic");
    expect(chip1).toHaveAttribute("title", "Source: Discogs (Style/Genre)");

    const chip2 = screen.getByText("Fiction");
    expect(chip2).toHaveAttribute("title", "Source: OpenLibrary (Subject)");

    const chip3 = screen.getByText("Favorites");
    expect(chip3).toHaveAttribute("title", "Source: User Curation");

    const chip4 = screen.getByText("Generic");
    expect(chip4).toHaveAttribute("title", "Source: Catalog Ingestion");
  });
});
