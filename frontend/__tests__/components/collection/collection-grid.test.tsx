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
 * Tests for the CollectionGrid component.
 *
 * CollectionGrid is a pure component: it accepts an array of Item objects and
 * renders either an empty state or a grid of ItemCards.
 * next/link is mocked globally via vitest.setup.ts.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import type { Item } from "@/types/frbr";
import { CollectionGrid } from "@/components/collection/collection-grid";

/**
 * Factory for creating mock Items.
 *
 * @param id - Item ID
 * @param title - Item title
 * @param author - Item author
 * @returns {Item} Mock Item
 */
function makeItem(id: number, title: string, author: string): Item {
  return {
    id,
    manifestation_id: id,
    owner_id: "user1",
    status: "unread",
    collection_status: "available",
    meta: {},
    title,
    authors: [author],
  };
}

describe("CollectionGrid", () => {
  it("shows an empty-state heading when the items array is empty", () => {
    render(<CollectionGrid items={[]} />);
    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders a helpful text in the empty state", () => {
    render(<CollectionGrid items={[]} />);
    expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument();
  });

  it("renders one card per item", () => {
    const items = [
      makeItem(1, "Dune", "Frank Herbert"),
      makeItem(2, "Recursion", "Blake Crouch"),
      makeItem(3, "Project Hail Mary", "Andy Weir"),
    ];
    render(<CollectionGrid items={items} />);
    expect(screen.getAllByText("Dune").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Recursion").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Project Hail Mary").length).toBeGreaterThan(0);
  });

  it("does not show the empty-state when items are present", () => {
    const items = [makeItem(1, "Dune", "Frank Herbert")];
    render(<CollectionGrid items={items} />);
    expect(screen.queryByText("No items found")).not.toBeInTheDocument();
  });

  it("creates links with correct item hrefs", () => {
    const items = [makeItem(7, "Neuromancer", "William Gibson")];
    render(<CollectionGrid items={items} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/item/7");
  });
});
