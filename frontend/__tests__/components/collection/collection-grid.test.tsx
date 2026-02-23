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

function makeItem(id: number, title: string, author: string): Item {
  return {
    id,
    manifestation_id: id,
    owner_id: "user1",
    status: "available",
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
    expect(screen.getByText("Dune")).toBeInTheDocument();
    expect(screen.getByText("Recursion")).toBeInTheDocument();
    expect(screen.getByText("Project Hail Mary")).toBeInTheDocument();
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
