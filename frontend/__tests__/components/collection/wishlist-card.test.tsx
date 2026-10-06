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
 * Tests for the WishlistCard component.
 *
 * Validates cover image rendering, unoptimized prop enforcement,
 * fallback behavior for external/legacy covers, and removal actions.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { WishlistItem } from "@/types/frbr";
import { WishlistCard } from "@/components/collection/wishlist-card";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "sonner";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

const mockDeleteMutateAsync = vi.fn();
vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useDeleteWishlistItem: () => ({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    }),
  };
});

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

/**
 * Render component wrapped in QueryClientProvider.
 *
 * @param ui - The React element to render.
 * @returns Rendered component result.
 */
const renderWithQuery = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);

/**
 * Creates a mock WishlistItem for unit testing.
 *
 * @param overrides - Partial overrides to customize the wishlist item.
 * @returns Fully populated mock WishlistItem.
 */
function makeWishlistItem(overrides: Partial<WishlistItem> = {}): WishlistItem {
  return {
    id: 10,
    work_id: 100,
    expression_id: 200,
    manifestation_id: 300,
    owner_id: "user-1",
    status: "want_to_read",
    collection_status: "wish_list",
    is_hidden: false,
    title: "The Hobbit",
    authors: ["J.R.R. Tolkien"],
    isbn: "9780261102217",
    publisher: "HarperCollins",
    cover_url: "/static/covers/hobbit.jpg",
    cover_status: "ready",
    content_type: "book",
    work_type: "book",
    medium_type: "book",
    is_owner: true,
    tags: [],
    added_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("WishlistCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Horizontal variant (Dashboard CurrentContext)", () => {
    it("renders cover image with unoptimized attribute for local cover path", () => {
      renderWithQuery(<WishlistCard item={makeWishlistItem()} variant="horizontal" />);
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "/api/static/covers/hobbit.jpg");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("renders cover image with unoptimized attribute for legacy external URL", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: "https://covers.openlibrary.org/b/id/8225266-M.jpg",
          })}
          variant="horizontal"
        />
      );
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "https://covers.openlibrary.org/b/id/8225266-M.jpg");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("falls back to manifestation_meta cover_url when primary cover_url is null", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: null,
            manifestation_meta: {
              cover_url: "/static/covers/from-meta.jpg",
            },
          })}
          variant="horizontal"
        />
      );
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "/api/static/covers/from-meta.jpg");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("falls back to manifestation_meta external cover_url when primary cover_url is null", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: null,
            manifestation_meta: {
              cover_url: "https://books.google.com/books/content?id=xyz",
            },
          })}
          variant="horizontal"
        />
      );
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "https://books.google.com/books/content?id=xyz");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("renders placeholder icon when no cover is available", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: null,
            manifestation_meta: {},
          })}
          variant="horizontal"
        />
      );
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });

    it("links to manifestation detail page when manifestation_id exists", () => {
      renderWithQuery(<WishlistCard item={makeWishlistItem({ manifestation_id: 300 })} variant="horizontal" />);
      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/manifestation/300");
    });

    it("links to /wishlist when manifestation_id is missing", () => {
      renderWithQuery(<WishlistCard item={makeWishlistItem({ manifestation_id: null })} variant="horizontal" />);
      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/wishlist");
    });

    it("displays title and author", () => {
      renderWithQuery(<WishlistCard item={makeWishlistItem()} variant="horizontal" />);
      expect(screen.getByText("The Hobbit")).toBeInTheDocument();
      expect(screen.getByText("J.R.R. Tolkien")).toBeInTheDocument();
    });
  });

  describe("Grid variant (Wishlist Page & Collection Wishlist view)", () => {
    it("renders cover image with unoptimized attribute for local cover path", () => {
      renderWithQuery(<WishlistCard item={makeWishlistItem()} variant="grid" />);
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "/api/static/covers/hobbit.jpg");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("renders cover image with unoptimized attribute for external cover URL", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: "https://covers.openlibrary.org/b/id/8225266-M.jpg",
          })}
          variant="grid"
        />
      );
      const img = screen.getByRole("img", { name: "The Hobbit" });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "https://covers.openlibrary.org/b/id/8225266-M.jpg");
      expect(img).toHaveAttribute("data-unoptimized", "true");
    });

    it("renders placeholder icon when cover_url is missing", () => {
      renderWithQuery(
        <WishlistCard
          item={makeWishlistItem({
            cover_url: null,
            manifestation_meta: {},
          })}
          variant="grid"
        />
      );
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });

    it("triggers remove action when remove button is clicked", async () => {
      mockDeleteMutateAsync.mockResolvedValueOnce({ id: 10 });
      renderWithQuery(<WishlistCard item={makeWishlistItem({ id: 10 })} variant="grid" />);
      const removeBtn = screen.getByRole("button", { name: /remove from wishlist/i });
      fireEvent.click(removeBtn);

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith(10);
        expect(toast.success).toHaveBeenCalledWith("Removed from wishlist");
      });
    });
  });
});
