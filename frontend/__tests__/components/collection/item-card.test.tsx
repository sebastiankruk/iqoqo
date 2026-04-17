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
 * Tests for the ItemCard component.
 *
 * ItemCard is a pure presentational component – no hooks, just props.
 * next/link is mocked globally via vitest.setup.ts.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import type { Item, CatalogEntry } from "@/types/frbr";
import { ItemCard } from "@/components/collection/item-card";

/**
 * Make a mock Item.
 *
 * @param overrides - Item overrides
 * @returns {Item} Mock Item
 */
function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 1,
    manifestation_id: 1,
    owner_id: "user1",
    status: "unread",
    collection_status: "available",
    meta: {},
    title: "Dune",
    authors: ["Frank Herbert"],
    ...overrides,
  };
}

/**
 * Make a mock CatalogEntry.
 *
 * @param overrides - CatalogEntry overrides
 * @returns {CatalogEntry} Mock CatalogEntry
 */
function makeCatalogEntry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 1,
    expression_id: 1,
    title: "Dune",
    authors: ["Frank Herbert"],
    meta: {},
    user_owns: false,
    ...overrides,
  };
}

describe("ItemCard", () => {
  it("displays the item title", () => {
    render(<ItemCard item={makeItem()} />);
    expect(screen.getAllByText("Dune").length).toBeGreaterThan(0);
  });

  it("displays the first author name", () => {
    render(<ItemCard item={makeItem()} />);
    expect(screen.getAllByText("Frank Herbert").length).toBeGreaterThan(0);
  });

  it("falls back to 'Untitled' when title is missing", () => {
    render(<ItemCard item={makeItem({ title: undefined })} />);
    expect(screen.getAllByText("Untitled").length).toBeGreaterThan(0);
  });

  it("falls back to 'Unknown author' when authors is missing", () => {
    render(<ItemCard item={makeItem({ authors: undefined })} />);
    expect(screen.getAllByText("Unknown author").length).toBeGreaterThan(0);
  });

  it("links to the item detail page", () => {
    render(<ItemCard item={makeItem({ id: 42 })} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/item/42");
  });

  it("renders a cover placeholder when coverUrl is absent", () => {
    render(<ItemCard item={makeItem({ meta: {}, manifestation_meta: {} })} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'available'", () => {
    render(<ItemCard item={makeItem({ collection_status: "available", status: "unread" })} />);
    expect(screen.getByTitle("Unread")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lent'", () => {
    render(<ItemCard item={makeItem({ collection_status: "lent" })} />);
    expect(screen.getByTitle("Lent Out")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'wish_list'", () => {
    render(<ItemCard item={makeItem({ collection_status: "wish_list" })} />);
    expect(screen.getByTitle("On Wish List")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lost'", () => {
    render(<ItemCard item={makeItem({ collection_status: "lost" })} />);
    expect(screen.getByTitle("Lost")).toBeInTheDocument();
  });

  it("renders a cover image when coverUrl is provided in meta", () => {
    render(<ItemCard item={makeItem({ meta: { cover_url: "https://example.com/cover.jpg" } })} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/cover.jpg");
    expect(img).toHaveAttribute("alt", "Cover of Dune");
  });

  it("links to the manifestation detail page when isManifestationView is true", () => {
    render(<ItemCard item={makeCatalogEntry({ id: 99 })} isManifestationView={true} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/manifestation/99");
  });

  it("hides the user item status dot when isManifestationView is true", () => {
    render(<ItemCard item={makeCatalogEntry()} isManifestationView={true} />);
    expect(screen.queryByTitle("On Shelf")).not.toBeInTheDocument();
  });

  it("shows 'In Collection' badge when isManifestationView is true and user_owns is true", () => {
    render(<ItemCard item={makeCatalogEntry({ user_owns: true })} isManifestationView={true} />);
    expect(screen.getByText("In Collection")).toBeInTheDocument();
  });

  it("does not show 'In Collection' badge when user_owns is false", () => {
    render(<ItemCard item={makeCatalogEntry({ user_owns: false })} isManifestationView={true} />);
    expect(screen.queryByText("In Collection")).not.toBeInTheDocument();
  });

  it("renders a cover image in horizontal variant when coverUrl is provided", () => {
    render(
      <ItemCard
        item={makeItem({ meta: { cover_url: "https://example.com/horizontal-cover.jpg" } })}
        variant="horizontal"
      />
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/horizontal-cover.jpg");
    expect(img).toHaveAttribute("alt", "Cover of Dune");
  });

  it("renders a cover placeholder in horizontal variant when coverUrl is absent", () => {
    render(<ItemCard item={makeItem({ meta: {} })} variant="horizontal" />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("does not show 'In Collection' badge when owner_id is 'Unavailable'", () => {
    render(<ItemCard item={makeItem({ owner_id: "Unavailable" })} />);
    expect(screen.queryByText("In Collection")).not.toBeInTheDocument();
  });
});
