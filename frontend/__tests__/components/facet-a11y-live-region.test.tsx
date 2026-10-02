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
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
/**
 * Tests for the facet ARIA live region in the collection page.
 *
 * Verifies that:
 * - An `aria-live="polite"` element is present
 * - Announcement text updates when filters are toggled
 * - Announcement text updates when all filters are cleared
 * - The element has sr-only visual hiding class
 */
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

// ── Mock hooks ─────────────────────────────────────────────────────────────
vi.mock("@/lib/api/hooks", () => ({
  useInfiniteItems: vi.fn(),
  useStats: vi.fn(),
  useProfile: vi.fn(),
  useInfiniteManifestations: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
  useInfiniteWorksShelf: vi.fn(),
  useInfiniteExpressionsShelf: vi.fn(),
  useTaxonomies: vi.fn(() => ({
    data: {
      collections: [],
      tags: [],
      genres: [],
      publishers: [],
    },
    isLoading: false,
  })),
  useFacetStats: vi.fn().mockReturnValue({
    data: {
      status_counts: { available: 10 },
      category_counts: {},
      format_counts: {},
    },
  }),
  queryKeys: { item: vi.fn((id: number) => ["item", id]) },
}));

// ── Stub sub-components ────────────────────────────────────────────────────
vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/collection/collection-grid", () => ({
  CollectionGrid: () => <div data-testid="collection-grid" />,
}));

vi.mock("@/components/collection/mobile-filter-drawer", () => ({
  MobileFilterDrawer: () => <div data-testid="mobile-filter-drawer" />,
}));

vi.mock("@/components/collection/sidebar-filters", () => ({
  SidebarFilters: () => <div data-testid="sidebar-filters" />,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => (
    <button {...(props as Record<string, unknown>)}>{children}</button>
  ),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      searchResults: "Search Results",
      foundOne: "1 result found",
      foundMultiple: "{count} results found",
      browseManage: "Browse your collection",
      title: "My Collection",
      showFilters: "Show Filters",
      showResults: "Show Results",
      secStatus: "Status",
      secFormats: "Formats",
      secMyCollections: "Collections",
      secTags: "Tags",
      secGenres: "Genres",
      secPublishers: "Publishers",
      secCuration: "Curation",
      noCover: "No Cover",
      noId: "No ID",
    };
    return translations[key] || key;
  },
  useLocale: () => "en",
}));

vi.mock("@/components/scanner/scanner-integration", () => ({
  ScannerIntegration: () => <div data-testid="scanner-integration" />,
}));

// ── Imports ────────────────────────────────────────────────────────────────
import {
  useInfiniteItems,
  useStats,
  useProfile,
  useInfiniteManifestations,
  useInfiniteWorksShelf,
  useInfiniteExpressionsShelf,
} from "@/lib/api/hooks";
import CollectionPage from "@/app/collection/page";

const mockUseItems = vi.mocked(useInfiniteItems);
const mockUseManifestations = vi.mocked(useInfiniteManifestations);
const mockUseWorksShelf = vi.mocked(useInfiniteWorksShelf);
const mockUseExpressionsShelf = vi.mocked(useInfiniteExpressionsShelf);

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

/**
 * Render component with QueryClientProvider.
 *
 * @param ui - Component to render
 * @returns The Testing Library render result.
 */
function renderWithProviders(ui: React.ReactElement) {
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * Generates mock infinite query results for Vitest tests.
 *
 * @param overrides - Optional overrides for the result object
 * @returns Mock infinite query result object
 */
function infiniteQueryResult(overrides: Record<string, unknown> = {}) {
  return {
    data: { pages: [] },
    isLoading: false,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
    ...overrides,
  } as never;
}

describe("Facet ARIA Live Region", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [{ data: [], meta: { total: 0, page: 1, pages: 1, limit: 20 } }] },
      })
    );

    mockUseManifestations.mockReturnValue(infiniteQueryResult());

    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());

    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());

    vi.mocked(useProfile).mockReturnValue({
      data: { id: "test-user", email: "test@iqoqo.local", permissions: [] },
    } as never);

    vi.mocked(useStats).mockReturnValue({
      data: {
        works: 0,
        expressions: 0,
        manifestations: 0,
        items: 0,
        total_items: 0,
        lent_items: 0,
        to_read: 0,
      },
    } as never);
  });

  it("renders exactly one polite live region", () => {
    renderWithProviders(<CollectionPage />);

    // `expect(queryByRole("status")).toBeDefined()` was here, and it passes for a
    // missing element: testing-library's queryBy* returns `null`, and `null` is
    // not `undefined`. The follow-up assertion, `toBeGreaterThanOrEqual(0)`, is
    // true for every length a NodeList can have. Between them the test could not
    // fail even with the live region deleted from page.tsx.
    const liveElements = document.querySelectorAll('[aria-live="polite"]');
    expect(liveElements).toHaveLength(1);
    expect(liveElements[0]).toBeInTheDocument();
  });

  it("visually hides the live region without hiding it from assistive tech", () => {
    const { container } = renderWithProviders(<CollectionPage />);

    // Was guarded by `if (liveElements.length > 0)`, so it passed vacuously
    // whenever the region was absent. The class is what keeps the announcement
    // out of the visual layout while leaving it in the accessibility tree, so
    // losing it is a real regression and the assertion must not be conditional.
    const liveElement = container.querySelector('[aria-live="polite"]');
    expect(liveElement).not.toBeNull();
    expect(liveElement).toHaveClass("sr-only");
  });

  it("announces that no filters are active when none are", () => {
    const { container } = renderWithProviders(<CollectionPage />);

    const liveElement = container.querySelector('[aria-live="polite"]');
    expect(liveElement?.textContent).toContain("All filters cleared");
    expect(liveElement?.textContent).toMatch(/\d+ results found/);
  });

  it("announces the active filter labels and result count", () => {
    // `activeFilters` is initialised from the URL (`page.tsx:125`), and
    // `vitest.setup.ts` mocks `useSearchParams` to an empty URLSearchParams, so
    // an active-filter case has to set it explicitly. The file's header comment
    // claimed to cover "announcement text updates when filters are toggled" and
    // no test did: every one of them rendered the unfiltered page.
    // `vitest.setup.ts` mocks `useSearchParams` to an empty `URLSearchParams`,
    // and the declared return type is Next's `ReadonlyURLSearchParams`. The page
    // only calls `.toString()` on it, so the cast is safe and keeps the change
    // local rather than widening the shared module mock.
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams("statuses=available&tags=horror,classic") as never);

    const { container } = renderWithProviders(<CollectionPage />);

    const liveElement = container.querySelector('[aria-live="polite"]');
    const text = liveElement?.textContent ?? "";

    // page.tsx: `Filtered to ${labels}. ${total} results found.`
    expect(text).toContain("Filtered to");
    expect(text).not.toContain("All filters cleared");
    expect(text).toMatch(/\d+ results found\./);
    // Both facets must be named, so a regression that announced only the first
    // filter -- leaving a screen-reader user unaware their other filters applied
    // -- fails here. The text carries display labels, not raw URL values:
    // `statuses=available` announces as "Status: On Shelf". Asserting the raw
    // value would be wrong, and asserting only the label would not prove both
    // facets are present, so the label prefixes are checked directly.
    expect(text).toContain("Status:");
    expect(text.match(/Tag:/g)).toHaveLength(2);
    expect(text).toContain("horror");
    expect(text).toContain("classic");
  });

  it("returns to the cleared announcement when the filters go away", () => {
    // The other direction of "updates when filters are toggled": clearing must
    // be announced too, otherwise the stale "Filtered to ..." text stays in the
    // live region and a screen reader is never told the view is unfiltered.
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams("statuses=available") as never);
    const { container, unmount } = renderWithProviders(<CollectionPage />);
    expect(container.querySelector('[aria-live="polite"]')?.textContent).toContain("Filtered to");

    unmount();
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as never);
    const cleared = renderWithProviders(<CollectionPage />);
    expect(cleared.container.querySelector('[aria-live="polite"]')?.textContent).toContain("All filters cleared");
  });
});
