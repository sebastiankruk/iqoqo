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
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CollectionPage from "@/app/collection/page";
import * as hooks from "@/lib/api/hooks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/collection",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

// Mock hooks
vi.mock("@/lib/api/hooks", () => ({
  useInfiniteItems: vi.fn(),
  useInfiniteManifestations: vi.fn(),
  useProfile: vi.fn(),
  useStats: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
  useInfiniteWorksShelf: vi.fn(),
  useInfiniteExpressionsShelf: vi.fn(),
  useTaxonomies: vi.fn(() => ({
    data: { collections: [], tags: [], genres: [], publishers: [] },
    isLoading: false,
  })),
  useFacetStats: vi.fn().mockReturnValue({
    data: {
      status_counts: {},
      category_counts: {},
      format_counts: {},
    },
  }),
}));

// Stub sub-components to keep test fast and focused on SEO JSON-LD
vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));
vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));
vi.mock("@/components/collection/sidebar-filters", () => ({
  SidebarFilters: () => <div data-testid="sidebar-filters" />,
}));
vi.mock("@/components/collection/collection-grid", () => ({
  CollectionGrid: () => <div data-testid="collection-grid" />,
}));
vi.mock("@/components/collection/mobile-filter-drawer", () => ({
  MobileFilterDrawer: () => <div data-testid="mobile-filter-drawer" />,
}));
vi.mock("@/components/collection/share-collection-dialog", () => ({
  ShareCollectionDialog: () => <div data-testid="share-dialog" />,
}));
vi.mock("@/components/collection/bulk-add-toolbar", () => ({
  BulkAddToolbar: () => <div data-testid="bulk-add-toolbar" />,
}));
vi.mock("@/components/collection/roadmap-view", () => ({
  RoadmapView: () => <div data-testid="roadmap-view" />,
}));

const createTestQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithQueryClient = (ui: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(<QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>);
};

describe("CollectionPage Schema.org SEO Structured Data", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(hooks.useInfiniteWorksShelf).mockReturnValue({
      data: { pages: [] },
      isLoading: false,
    } as any);

    vi.mocked(hooks.useInfiniteExpressionsShelf).mockReturnValue({
      data: { pages: [] },
      isLoading: false,
    } as any);
  });

  it("should render schema:CollectionPage with ItemList and item references", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: {
        id: 1,
        display_name: "Alice Reader",
        public_username: "alice",
      },
    } as any);

    const mockItems = [
      { id: 101, title: "Dune", content_type: "book" },
      { id: 102, title: "Neuromancer", content_type: "book" },
    ];

    vi.mocked(hooks.useInfiniteItems).mockReturnValue({
      data: {
        pages: [
          {
            data: mockItems,
            meta: { total: 2 },
          },
        ],
      },
      isLoading: false,
    } as any);

    vi.mocked(hooks.useInfiniteManifestations).mockReturnValue({
      data: { pages: [] },
      isLoading: false,
    } as any);

    const { container } = renderWithQueryClient(<CollectionPage />);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("CollectionPage");
    expect(jsonLd["name"]).toBe("Alice Reader's Collection");
    expect(jsonLd["numberOfItems"]).toBe(2);
    expect(jsonLd["author"]["name"]).toBe("Alice Reader");

    const mainEntity = jsonLd["mainEntity"];
    expect(mainEntity).toBeDefined();
    expect(mainEntity["@type"]).toBe("ItemList");
    expect(mainEntity["numberOfItems"]).toBe(2);
    expect(mainEntity["itemListElement"]).toHaveLength(2);
    expect(mainEntity["itemListElement"][0]["item"]["name"]).toBe("Dune");
    expect(mainEntity["itemListElement"][0]["item"]["@type"]).toBe("Book");
    expect(mainEntity["itemListElement"][1]["item"]["name"]).toBe("Neuromancer");
    expect(mainEntity["itemListElement"][1]["item"]["@type"]).toBe("Book");
  });

  it("should not render JSON-LD script tag when profile is unavailable", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: null,
    } as any);

    vi.mocked(hooks.useInfiniteItems).mockReturnValue({
      data: { pages: [] },
      isLoading: false,
    } as any);

    vi.mocked(hooks.useInfiniteManifestations).mockReturnValue({
      data: { pages: [] },
      isLoading: false,
    } as any);

    const { container } = renderWithQueryClient(<CollectionPage />);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).toBeNull();
  });
});
