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

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import WishlistPage from "@/app/wishlist/page";

const mockUseWishlist = vi.fn();

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useWishlist: (params?: Record<string, unknown>, enabled?: boolean) => mockUseWishlist(params, enabled),
  };
});

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("@/components/collection/wishlist-card", () => ({
  WishlistCard: ({ item }: { item: { id: number; title: string } }) => (
    <div data-testid="wishlist-card">{item.title}</div>
  ),
}));

/** Render component wrapped in QueryClientProvider. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("WishlistPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Add to Wishlist primary CTA linking to /scan?policy=wishlist", () => {
    mockUseWishlist.mockReturnValue({
      data: {
        data: [{ id: 1, title: "Dune" }],
        total: 1,
      },
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<WishlistPage />);

    const addLinks = screen.getAllByRole("link", { name: /add to wishlist/i });
    expect(addLinks[0]).toHaveAttribute("href", "/scan?policy=wishlist");
    expect(screen.getByText("1 item")).toBeInTheDocument();
    expect(screen.getByTestId("wishlist-card")).toHaveTextContent("Dune");
  });

  it("passes search, category, and sort parameters to useWishlist", () => {
    mockUseWishlist.mockReturnValue({
      data: { data: [], total: 0 },
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<WishlistPage />);
    expect(mockUseWishlist).toHaveBeenCalledWith({ limit: 100 }, undefined);

    const searchInput = screen.getByPlaceholderText("Search wishlist...");
    fireEvent.change(searchInput, { target: { value: "Tolkien" } });

    const categorySelect = screen.getByLabelText("Filter by category");
    fireEvent.change(categorySelect, { target: { value: "music" } });

    const sortSelect = screen.getByLabelText("Sort wishlist");
    fireEvent.change(sortSelect, { target: { value: "title" } });

    expect(mockUseWishlist).toHaveBeenLastCalledWith(
      { limit: 100, q: "Tolkien", category: "music", sort: "title" },
      undefined
    );

    const clearBtn = screen.getByRole("button", { name: /clear filters/i });
    fireEvent.click(clearBtn);
    expect(mockUseWishlist).toHaveBeenLastCalledWith({ limit: 100 }, undefined);
  });

  it("renders localized category filter options", () => {
    mockUseWishlist.mockReturnValue({
      data: { data: [], total: 0 },
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<WishlistPage />);
    expect(screen.getByRole("option", { name: "Books & Text" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "LEGO Sets" })).toBeInTheDocument();
  });

  it("renders empty-state CTAs when wishlist has no items", () => {
    mockUseWishlist.mockReturnValue({
      data: { data: [], total: 0 },
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<WishlistPage />);

    expect(screen.getByText("Your wishlist is empty")).toBeInTheDocument();
    const browseLink = screen.getByRole("link", { name: /browse catalog/i });
    expect(browseLink).toHaveAttribute("href", "/collection?view=manifestations");
    const addLinks = screen.getAllByRole("link", { name: /add to wishlist/i });
    expect(addLinks.length).toBeGreaterThanOrEqual(2);
  });
});
