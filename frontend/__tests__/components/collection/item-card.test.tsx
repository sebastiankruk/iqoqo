/**
 * Tests for the ItemCard component.
 *
 * ItemCard is a pure presentational component – no hooks, just props.
 * next/link is mocked globally via vitest.setup.ts.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import type { Item } from "@/types/frbr";
import { ItemCard } from "@/components/collection/item-card";

function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 1,
    manifestation_id: 1,
    owner_id: "user1",
    status: "available",
    meta: {},
    title: "Dune",
    authors: ["Frank Herbert"],
    ...overrides,
  };
}

describe("ItemCard", () => {
  it("displays the item title", () => {
    render(<ItemCard item={makeItem()} />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
  });

  it("displays the first author name", () => {
    render(<ItemCard item={makeItem()} />);
    expect(screen.getByText("Frank Herbert")).toBeInTheDocument();
  });

  it("falls back to 'Untitled' when title is missing", () => {
    render(<ItemCard item={makeItem({ title: undefined })} />);
    expect(screen.getByText("Untitled")).toBeInTheDocument();
  });

  it("falls back to 'Unknown author' when authors is missing", () => {
    render(<ItemCard item={makeItem({ authors: undefined })} />);
    expect(screen.getByText("Unknown author")).toBeInTheDocument();
  });

  it("links to the item detail page", () => {
    render(<ItemCard item={makeItem({ id: 42 })} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/item/42");
  });

  it("renders a cover placeholder when coverUrl is absent", () => {
    render(<ItemCard item={makeItem({ meta: {}, manifestation_meta: {} })} />);
    // Should not render an img; renders the BookOpen icon instead
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'available'", () => {
    render(<ItemCard item={makeItem({ status: "available" })} />);
    expect(screen.getByTitle("On Shelf")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lent'", () => {
    render(<ItemCard item={makeItem({ status: "lent" })} />);
    expect(screen.getByTitle("Lent Out")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'wish_list'", () => {
    render(<ItemCard item={makeItem({ status: "wish_list" })} />);
    expect(screen.getByTitle("On Wish List")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lost'", () => {
    render(<ItemCard item={makeItem({ status: "lost" })} />);
    expect(screen.getByTitle("Lost")).toBeInTheDocument();
  });

  it("renders a cover image when coverUrl is provided in meta", () => {
    render(
      <ItemCard
        item={makeItem({ meta: { cover_url: "https://example.com/cover.jpg" } })}
      />,
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/cover.jpg");
    expect(img).toHaveAttribute("alt", "Cover of Dune");
  });
});
