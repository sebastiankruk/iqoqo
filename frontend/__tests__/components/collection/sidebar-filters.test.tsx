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
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useTaxonomies } from "@/lib/api/hooks";

// Mock useTaxonomies
vi.mock("@/lib/api/hooks", () => ({
  useTaxonomies: vi.fn(),
  useManifestationWithPolling: vi.fn(data => ({ item: data })),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  queryKeys: { item: vi.fn() },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("SidebarFilters with Searchable Facets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const taxonomies = {
      genres: ["Fantasy", "Sci-Fi", "Mystery", "Thriller", "Romance", "Horror"],
      tags: ["Read", "Unread", "Favorite", "To Read", "Borrowed", "Reference"],
      publishers: ["Penguin", "Tor", "Bantam", "Del Rey", "HarperCollins", "Macmillan"],
      collections: ["My Collection", "Favorites", "To Read", "Wishlist", "School", "Work"],
    };
    vi.mocked(useTaxonomies).mockReturnValue({ data: taxonomies } as unknown as ReturnType<typeof useTaxonomies>);
  });

  const renderComponent = (activeFilters: ActiveFilter[] = []) =>
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters activeFilters={activeFilters} onToggleFilter={vi.fn()} />
      </QueryClientProvider>
    );

  it("renders correctly and filters facets based on user input", async () => {
    renderComponent();

    // Media Category should be visible
    expect(screen.getByText("Media Category")).toBeInTheDocument();

    // Sections that are closed by default (Genres)
    const genreButton = screen.getByText("Genres");
    fireEvent.click(genreButton);

    // Now options should be visible
    expect(screen.getByText("Fantasy")).toBeInTheDocument();
    expect(screen.getByText("Sci-Fi")).toBeInTheDocument();

    // Search/Filter the facet
    const searchInput = screen.getByPlaceholderText("Find genre...");
    fireEvent.change(searchInput, { target: { value: "Fant" } });

    expect(screen.getByText("Fantasy")).toBeInTheDocument();
    expect(screen.queryByText("Sci-Fi")).not.toBeInTheDocument();
  });

  it("calls onToggleFilter when an option is clicked", async () => {
    const mockToggle = vi.fn();
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters activeFilters={[]} onToggleFilter={mockToggle} />
      </QueryClientProvider>
    );

    const genreButton = screen.getByText("Genres");
    fireEvent.click(genreButton);

    const fantasyOption = screen.getByText("Fantasy");
    fireEvent.click(fantasyOption);

    expect(mockToggle).toHaveBeenCalledWith({ type: "genre", value: "Fantasy" });
  });

  it("passes correct scope based on isLoggedIn prop", () => {
    // 1. When isLoggedIn is false (default)
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters activeFilters={[]} onToggleFilter={vi.fn()} isLoggedIn={false} />
      </QueryClientProvider>
    );
    expect(useTaxonomies).toHaveBeenLastCalledWith({ scope: "global", filters: {} });

    // 2. When isLoggedIn is true
    rerender(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters activeFilters={[]} onToggleFilter={vi.fn()} isLoggedIn={true} />
      </QueryClientProvider>
    );
    expect(useTaxonomies).toHaveBeenLastCalledWith({ scope: "user", filters: {} });
  });
});

describe("SidebarFilters Cross-Filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTaxonomies).mockReturnValue({
      data: {
        genres: [],
        tags: [],
        publishers: [],
        collections: [],
      },
    } as unknown as ReturnType<typeof useTaxonomies>);
  });

  it("applies opacity-50 to status options with zero count when not selected", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          statusCounts={{ wish_list: 0, available: 5, ordered: 0 }}
        />
      </QueryClientProvider>
    );

    const wishListLabel = screen.getByText("On Wish List").closest("label");
    const availableLabel = screen.getByText("On Shelf").closest("label");

    expect(wishListLabel?.className).toContain("opacity-50");
    expect(availableLabel?.className).not.toContain("opacity-50");
  });

  it("keeps zero-count status enabled if currently selected", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[{ type: "status", value: "wish_list" }]}
          onToggleFilter={vi.fn()}
          statusCounts={{ wish_list: 0, available: 5 }}
        />
      </QueryClientProvider>
    );

    const wishListCheckbox = screen.getByRole("checkbox", { name: "On Wish List 0" });
    expect(wishListCheckbox).not.toBeDisabled();
  });

  it("disables unchecked zero-count status inputs", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters activeFilters={[]} onToggleFilter={vi.fn()} statusCounts={{ wish_list: 0, ordered: 0 }} />
      </QueryClientProvider>
    );

    const wishListCheckbox = screen.getByRole("checkbox", { name: "On Wish List 0" });
    expect(wishListCheckbox).toBeDisabled();
  });
});

describe("SearchableFacet counts display", () => {
  const mockTaxonomies = {
    genres: ["Fantasy", "Horror"],
    tags: ["english", "polish"],
    publishers: ["Penguin"],
    collections: ["Favorites"],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTaxonomies).mockReturnValue({
      data: mockTaxonomies,
    } as unknown as ReturnType<typeof useTaxonomies>);
  });

  const queryClient2 = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  it("shows count badges next to facet options when counts prop is provided", () => {
    render(
      <QueryClientProvider client={queryClient2}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          tagCounts={{ english: 5, polish: 2, german: 0 }}
          collectionCounts={{ Favorites: 3 }}
          genreCounts={{ Fantasy: 4, Horror: 1 }}
          publisherCounts={{ Penguin: 10 }}
        />
      </QueryClientProvider>
    );

    // Open Genres section
    fireEvent.click(screen.getByText("Genres"));
    expect(screen.getByText("Fantasy")).toBeInTheDocument();
    // Find count badge for Fantasy
    expect(screen.getByText("4")).toBeInTheDocument();

    // Open Tags section
    fireEvent.click(screen.getByText("Tags"));
    expect(screen.getByText("english")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("polish")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
  
  it("does not show count for items that have no count entry", () => {
    render(
      <QueryClientProvider client={queryClient2}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          tagCounts={{ english: 5 }}
        />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByText("Tags"));
    // 'polish' should exist but show no count badge (counts don't include it)
    expect(screen.getByText("english")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("polish")).toBeInTheDocument();
    // 'polish' count badge should NOT exist
    const polishEl = screen.getByText("polish");
    // No "2" badge sibling since not in counts
  });

  it("renders labels normally for 0-count facet items", () => {
    render(
      <QueryClientProvider client={queryClient2}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          tagCounts={{ english: 0, polish: 0 }}
        />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByText("Tags"));
    expect(screen.getByText("english")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(1);
  });
});
