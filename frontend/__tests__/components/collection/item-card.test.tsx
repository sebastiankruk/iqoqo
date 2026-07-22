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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Item, CatalogEntry } from "@/types/frbr";
import { ItemCard } from "@/components/collection/item-card";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    delete: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWithQuery = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);

/**
 * Make a mock Item.
 *
 * @param overrides - Partial overrides for the Item.
 * @returns A fully populated mock Item.
 */
function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 1,
    manifestation_id: 1,
    owner_id: "user1",
    status: "want_to_read",
    collection_status: "available",
    meta: {},
    title: "Dune",
    authors: ["Frank Herbert"],
    is_owner: true,
    ...overrides,
  };
}

/**
 * Make a mock CatalogEntry.
 *
 * @param overrides - Partial overrides for the CatalogEntry.
 * @returns A fully populated mock CatalogEntry.
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays the item title", () => {
    renderWithQuery(<ItemCard item={makeItem()} />);
    expect(screen.getAllByText("Dune").length).toBeGreaterThan(0);
  });

  it("displays the first author name", () => {
    renderWithQuery(<ItemCard item={makeItem()} />);
    expect(screen.getAllByText("Frank Herbert").length).toBeGreaterThan(0);
  });

  it("falls back to 'Untitled' when title is missing", () => {
    renderWithQuery(<ItemCard item={makeItem({ title: undefined })} />);
    expect(screen.getAllByText("Untitled").length).toBeGreaterThan(0);
  });

  it("falls back to 'Unknown author' when authors is missing", () => {
    renderWithQuery(<ItemCard item={makeItem({ authors: undefined })} />);
    expect(screen.getAllByText("Unknown author").length).toBeGreaterThan(0);
  });

  it("links to the item detail page", () => {
    renderWithQuery(<ItemCard item={makeItem({ id: 42 })} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/item/42");
  });

  it("shows a quantity badge when _quantity > 1", () => {
    const item = makeItem();
    (item as Item & { _quantity?: number })._quantity = 3;
    renderWithQuery(<ItemCard item={item} />);
    expect(screen.getByText("x3")).toBeInTheDocument();
  });

  it("does not show a quantity badge when _quantity is 1 or undefined", () => {
    const item = makeItem();
    renderWithQuery(<ItemCard item={item} />);
    expect(screen.queryByText(/^x\d+$/)).not.toBeInTheDocument();
  });

  it("renders a cover placeholder when coverUrl is absent", () => {
    renderWithQuery(<ItemCard item={makeItem({ meta: {}, manifestation_meta: {} })} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'available'", () => {
    renderWithQuery(<ItemCard item={makeItem({ collection_status: "available", status: "want_to_read" })} />);
    expect(screen.getByTitle("Want to Read")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lent'", () => {
    renderWithQuery(<ItemCard item={makeItem({ collection_status: "lent" })} />);
    expect(screen.getByTitle("Lent Out")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'wish_list'", () => {
    renderWithQuery(<ItemCard item={makeItem({ collection_status: "wish_list" })} />);
    expect(screen.getByTitle("On Wish List")).toBeInTheDocument();
  });

  it("shows a status dot with the correct title for 'lost'", () => {
    renderWithQuery(<ItemCard item={makeItem({ collection_status: "lost" })} />);
    expect(screen.getByTitle("Lost")).toBeInTheDocument();
  });

  it("renders a cover image when coverUrl is provided in meta", () => {
    renderWithQuery(<ItemCard item={makeItem({ meta: { cover_url: "https://example.com/cover.jpg" } })} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/cover.jpg");
    expect(img).toHaveAttribute("alt", "Cover of Dune");
  });

  it("links to the manifestation detail page when isManifestationView is true", () => {
    renderWithQuery(<ItemCard item={makeCatalogEntry({ id: 99 })} isManifestationView={true} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/manifestation/99");
  });

  it("hides the user item status dot when isManifestationView is true", () => {
    renderWithQuery(<ItemCard item={makeCatalogEntry()} isManifestationView={true} />);
    expect(screen.queryByTitle("On Shelf")).not.toBeInTheDocument();
  });

  it("shows 'In Collection' badge when isManifestationView is true and user_owns is true", () => {
    // When item_id is not present
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <ItemCard item={makeCatalogEntry({ user_owns: true, item_id: null })} isManifestationView={true} />
      </QueryClientProvider>
    );
    expect(screen.getByText(/In Collection/i)).toBeInTheDocument();

    // When item_id is present
    rerender(
      <QueryClientProvider client={queryClient}>
        <ItemCard item={makeCatalogEntry({ user_owns: true, item_id: 123 })} isManifestationView={true} />
      </QueryClientProvider>
    );
    expect(screen.getByText(/In Collection →/i)).toBeInTheDocument();
  });

  it("does not show 'In Collection' badge when user_owns is false", () => {
    renderWithQuery(<ItemCard item={makeCatalogEntry({ user_owns: false })} isManifestationView={true} />);
    expect(screen.queryByText("In Collection")).not.toBeInTheDocument();
    expect(screen.queryByText("In Collection →")).not.toBeInTheDocument();
  });

  it("renders a cover image in horizontal variant when coverUrl is provided", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ItemCard
          item={makeItem({ meta: { cover_url: "https://example.com/horizontal-cover.jpg" } })}
          variant="horizontal"
        />
      </QueryClientProvider>
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/horizontal-cover.jpg");
    expect(img).toHaveAttribute("alt", "Cover of Dune");
  });

  it("renders a cover placeholder in horizontal variant when coverUrl is absent", () => {
    renderWithQuery(<ItemCard item={makeItem({ meta: {} })} variant="horizontal" />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("does not show 'In Collection' badge when owner_id is 'Unavailable'", () => {
    renderWithQuery(<ItemCard item={makeItem({ owner_id: "Unavailable" })} />);
    expect(screen.queryByText("In Collection")).not.toBeInTheDocument();
  });

  it("renders gracefully when manifestation_id is null (virtual wishlist item)", () => {
    // Virtual wishlist items (UserWorkIntent adapters) have manifestation_id null/undefined.
    // The ItemCard must never crash when this field is missing.
    const virtualItem = makeItem({ id: -5, manifestation_id: undefined, title: "Virtual Book" });
    // Should render without throwing
    renderWithQuery(<ItemCard item={virtualItem} />);
    // Title still rendered
    expect(screen.getAllByText("Virtual Book").length).toBeGreaterThan(0);
    // Link still points to item page (not manifestation page)
    expect(screen.getByRole("link")).toHaveAttribute("href", "/item/-5");
  });

  it("renders wishlist drop button when collection_status is wish_list and user is owner", () => {
    renderWithQuery(<ItemCard item={makeItem({ id: -10, collection_status: "wish_list", is_owner: true })} />);
    expect(screen.getByLabelText("Remove from wishlist")).toBeInTheDocument();
  });

  it("does not render wishlist drop button when user is not owner", () => {
    renderWithQuery(<ItemCard item={makeItem({ id: -10, collection_status: "wish_list", is_owner: false })} />);
    expect(screen.queryByLabelText("Remove from wishlist")).not.toBeInTheDocument();
  });

  it("does not render wishlist drop button when collection_status is not wish_list", () => {
    renderWithQuery(<ItemCard item={makeItem({ collection_status: "available", is_owner: true })} />);
    expect(screen.queryByLabelText("Remove from wishlist")).not.toBeInTheDocument();
  });

  it("calls onWishlistRemove callback and API when wishlist button is clicked", async () => {
    const onWishlistRemove = vi.fn();
    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { success: true } });

    renderWithQuery(
      <ItemCard
        item={makeItem({ id: -10, collection_status: "wish_list", title: "Dune", is_owner: true })}
        onWishlistRemove={onWishlistRemove}
      />
    );

    const removeBtn = screen.getByLabelText("Remove from wishlist");
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/items/-10");
      expect(onWishlistRemove).toHaveBeenCalledWith(-10);
    });
  });

  it("shows error toast when wishlist removal fails", async () => {
    const { toast } = await import("sonner");
    vi.mocked(apiClient.delete).mockRejectedValueOnce(new Error("Network error"));

    renderWithQuery(<ItemCard item={makeItem({ id: -10, collection_status: "wish_list", is_owner: true })} />);

    fireEvent.click(screen.getByLabelText("Remove from wishlist"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Network error");
    });
  });

  it("shows HeartOff in horizontal variant for wishlist items owned by user", () => {
    renderWithQuery(
      <ItemCard
        item={makeItem({ id: -5, collection_status: "wish_list", title: "Wish Book", is_owner: true })}
        variant="horizontal"
      />
    );
    expect(screen.getByLabelText("Remove from wishlist")).toBeInTheDocument();
  });
});
