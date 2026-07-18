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
      genres: [
        "Fantasy",
        "Sci-Fi",
        "Mystery",
        "Thriller",
        "Romance",
        "Horror",
        "Non-fiction",
        "Biography",
        "History",
        "Poetry",
        "Drama",
      ],
      tags: ["Read", "Unread", "Favorite", "To Read", "Borrowed", "Reference"],
      publishers: ["Penguin", "Tor", "Bantam", "Del Rey", "HarperCollins", "Macmillan"],
      collections: ["My Collection", "Favorites", "To Read", "Wishlist", "School", "Work"],
    };
    vi.mocked(useTaxonomies).mockReturnValue({ data: taxonomies } as unknown as ReturnType<typeof useTaxonomies>);
  });

  const renderComponent = (activeFilters: ActiveFilter[] = []) =>
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={activeFilters}
          onToggleFilter={vi.fn()}
          isLoggedIn={true}
          genreCounts={{
            Fantasy: 1,
            "Sci-Fi": 1,
            Mystery: 1,
            Thriller: 1,
            Romance: 1,
            Horror: 1,
            "Non-fiction": 1,
            Biography: 1,
            History: 1,
            Poetry: 1,
            Drama: 1,
          }}
          tagCounts={{ english: 5 }}
        />
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
        <SidebarFilters activeFilters={[]} onToggleFilter={mockToggle} genreCounts={{ Fantasy: 1, "Sci-Fi": 1 }} />
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
        <SidebarFilters activeFilters={[]} onToggleFilter={vi.fn()} isLoggedIn={false} genreCounts={{ Fantasy: 1 }} />
      </QueryClientProvider>
    );
    expect(useTaxonomies).toHaveBeenLastCalledWith({ scope: "global", filters: {} });

    // 2. When isLoggedIn is true
    rerender(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={true}
          genreCounts={{ Fantasy: 1 }}
          tagCounts={{ english: 1 }}
        />
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
          isLoggedIn={true}
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
          isLoggedIn={true}
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
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={true}
          statusCounts={{ wish_list: 0, ordered: 0 }}
        />
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
          isLoggedIn={true}
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
        <SidebarFilters activeFilters={[]} onToggleFilter={vi.fn()} isLoggedIn={true} tagCounts={{ english: 5 }} />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByText("Tags"));
    // 'polish' should NOT exist because it has no count entry (defaults to 0) and is not active
    expect(screen.getByText("english")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.queryByText("polish")).not.toBeInTheDocument();
  });

  it("renders labels normally for 0-count facet items", () => {
    render(
      <QueryClientProvider client={queryClient2}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={true}
          tagCounts={{ english: 0, polish: 0 }}
        />
      </QueryClientProvider>
    );

    // The Tags section itself shouldn't even render if all tags have 0 counts and none are active
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });

  it("renders labels normally for 0-count facet items if they are active", () => {
    render(
      <QueryClientProvider client={queryClient2}>
        <SidebarFilters
          activeFilters={[{ type: "tag", value: "english" }]}
          onToggleFilter={vi.fn()}
          isLoggedIn={true}
          tagCounts={{ english: 0, polish: 0 }}
        />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByText("Tags"));
    expect(screen.getByText("english")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("polish")).not.toBeInTheDocument();
  });
});

describe("SidebarFilters — unauthenticated users", () => {
  const mockTaxonomies = {
    genres: ["Fantasy", "Fiction"],
    tags: ["favorites", "english"],
    publishers: ["Penguin"],
    collections: ["My Books", "Favorites"],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTaxonomies).mockReturnValue({
      data: mockTaxonomies,
    } as unknown as ReturnType<typeof useTaxonomies>);
  });

  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  it("hides Collection Status section for unauthenticated users", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={false}
          statusCounts={{ available: 5, wish_list: 3 }}
        />
      </QueryClientProvider>
    );

    expect(screen.queryByText("Collection Status")).not.toBeInTheDocument();
    expect(screen.queryByText("On Shelf")).not.toBeInTheDocument();
    expect(screen.queryByText("On Wish List")).not.toBeInTheDocument();
  });

  it("hides user-specific facets (Tags, Collections, Progress) for unauthenticated users", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={false}
          tagCounts={{ favorites: 3 }}
          collectionCounts={{ "My Books": 2 }}
        />
      </QueryClientProvider>
    );

    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
    expect(screen.queryByText("My Collections")).not.toBeInTheDocument();
  });

  it("shows global facets (Media Category, Genres, Publishers) for unauthenticated users", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SidebarFilters
          activeFilters={[]}
          onToggleFilter={vi.fn()}
          isLoggedIn={false}
          genreCounts={{ Fantasy: 5 }}
          publisherCounts={{ Penguin: 3 }}
          categoryCounts={{ text: 10 }}
        />
      </QueryClientProvider>
    );

    expect(screen.getByText("Media Category")).toBeInTheDocument();
    // Collection Status and Progress must be absent
    expect(screen.queryByText("Collection Status")).not.toBeInTheDocument();
    expect(screen.queryByText("Progress")).not.toBeInTheDocument();
  });
});
