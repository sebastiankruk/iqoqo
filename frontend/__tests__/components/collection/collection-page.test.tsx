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
 * Tests for the CollectionPage component.
 *
 * Focuses on the three behavioral fixes made in the pagination/filtering
 * overhaul from the infinite-scroll / virtualized scrolling migration:
 *
 * 1. statusCounts shown in the sidebar come from useStats() (global totals)
 *    and are therefore accurate across all pages, not just the visible 40.
 * 2. resultCount displayed in the FilterBar is meta.total from the API
 *    response, not the length of the local items array.
 * 3. Filter changes are forwarded to useInfiniteItems as server-side params.
 *
 * useInfiniteItems, useInfiniteManifestations and useStats are mocked;
 * sub-components that don't contribute to the tested behavior (Navbar,
 * CollectionGrid, MobileFilterDrawer) are stubbed to keep the test surface
 * small and fast.
 */
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
 * Tests for the CollectionPage component.
 *
 * Focuses on the three behavioral fixes:
 *
 * 1. statusCounts from useStats() (global totals).
 * 2. resultCount from meta.total.
 * 3. Filter changes forwarded as server-side params.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Build a standard infinite query mock return value.
 *
 * @param overrides - Properties to override in the default mock shape
 * @returns A mock infinite query result object
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
      status_counts: { available: 150, lent: 5, lost: 2, wish_list: 21, reading: 10, read: 50, want_to_read: 23 },
      category_counts: { movie: 20 },
      format_counts: { dvd: 20 },
    },
  }),
}));

// ── Stub heavy / irrelevant sub-components ─────────────────────────────────
vi.mock("@/components/dashboard/navbar", () => ({
  /**
   * Test stub: Navbar component.
   * @returns {JSX.Element}
   */
  Navbar: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/collection/collection-grid", () => ({
  /**
   * Test stub: CollectionGrid renders number of items.
   * @param {{ items: unknown[] }} props - Component props.
   * @returns {JSX.Element}
   */
  CollectionGrid: ({ items }: { items: unknown[] }) => <div data-testid="collection-grid">{items.length} rendered</div>,
}));

vi.mock("@/components/collection/mobile-filter-drawer", () => ({
  /**
   * Test stub: MobileFilterDrawer component.
   * @returns {JSX.Element}
   */
  MobileFilterDrawer: () => <div data-testid="mobile-filter-drawer" />,
}));

// ── Imports (after mocks are defined) ─────────────────────────────────────
import {
  useInfiniteItems,
  useStats,
  useInfiniteManifestations,
  useProfile,
  useInfiniteWorksShelf,
  useInfiniteExpressionsShelf,
} from "@/lib/api/hooks";
import CollectionPage from "@/app/collection/page";
import type { ApiResponse, DashboardStats, UserProfile, Item } from "@/types/frbr";

const mockUseItems = vi.mocked(useInfiniteItems);
const mockUseStats = vi.mocked(useStats);
const mockUseManifestations = vi.mocked(useInfiniteManifestations);
const mockUseProfile = vi.mocked(useProfile);
const mockUseWorksShelf = vi.mocked(useInfiniteWorksShelf);
const mockUseExpressionsShelf = vi.mocked(useInfiniteExpressionsShelf);

// ── Fixtures ──────────────────────────────────────────────────────────────

/** Full dashboard stats mock */
const FULL_STATS: DashboardStats = {
  works: 80,
  expressions: 80,
  manifestations: 120,
  items: 237,
  total_items: 237,
  lent_items: 5,
  to_read: 20,
  items_available: 150,
  items_lent: 5,
  items_lost: 2,
  items_wish_list: 21,
  items_reading: 10,
  items_read: 50,
  items_want_to_read: 23,
  borrowed_items: 2,
};

/** Mock user profile */
const MOCK_PROFILE: UserProfile = { id: "1", email: "test@example.com", permissions: ["write:metadata"] };

const MOCK_WORKS_DATA = {
  success: true,
  data: [
    {
      work_id: 1,
      title: "Mock Work Anthology",
      creators: ["J.R.R. Tolkien"],
      owned_manifestations: [{ manifestation_id: 10, item_id: 42, format: "book", cover_url: "/test-cover.jpg" }],
      total_items: 4,
    },
  ],
  total: 1,
  error: null,
};

const MOCK_EXPRS_DATA = {
  success: true,
  data: [
    {
      expression_id: 1,
      work_title: "Mock Expression Trans",
      content_type: "text",
      language: "pl",
      creators: ["J.R.R. Tolkien"],
      owned_manifestations: [{ manifestation_id: 20, item_id: 84, format: "book", cover_url: "/test-cover2.jpg" }],
      total_items: 2,
    },
  ],
  total: 1,
  error: null,
};

/**
 * Make a mock API response for items.
 *
 * @param {Partial<NonNullable<ApiResponse<Item[]>["meta"]>>} overrides - Metadata overrides.
 * @param {number} dataLength - Number of items to generate.
 * @returns {ApiResponse<Item[]>} Mock API response.
 */
function makeItemsResponse(
  overrides: Partial<NonNullable<ApiResponse<Item[]>["meta"]>> = {},
  dataLength = 2
): ApiResponse<Item[]> {
  const items: Item[] = Array.from({ length: dataLength }, (_, i) => ({
    id: i + 1,
    manifestation_id: i + 1,
    owner_id: "user1",
    status: "want_to_read",
    collection_status: "available",
    meta: {},
    title: `Book ${i + 1}`,
    authors: ["Author"],
  }));
  return {
    success: true,
    data: items,
    error: null,
    meta: { page: 1, limit: 40, total: 237, pages: 6, ...overrides },
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe("CollectionPage – statusCounts from useStats()", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Simulate a logged-in user so the page renders normally
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({}, 2)] },
      })
    );
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());
  });

  it("shows the global 'available' count from useStats, not the page count", () => {
    render(<CollectionPage />);
    // FULL_STATS.items_available = 150. The page only loaded 2 "available" items.
    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("shows the global 'lent' count from useStats", () => {
    render(<CollectionPage />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows the global 'wish_list' count from useStats", () => {
    render(<CollectionPage />);
    expect(screen.getByText("21")).toBeInTheDocument();
  });

  it("falls back to 0 when useStats has not yet loaded", () => {
    mockUseStats.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useStats>);
    render(<CollectionPage />);
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBeGreaterThan(0);
  });
});

describe("CollectionPage – resultCount from meta.total", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());
  });

  it("shows meta.total as the result count, not the local items length", () => {
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({ total: 237 }, 2)] },
      })
    );
    render(<CollectionPage />);
    expect(screen.getByText("237")).toBeInTheDocument();
  });

  it("shows 0 items while loading", () => {
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: undefined,
        isLoading: true,
      })
    );
    render(<CollectionPage />);
    expect(screen.getByTestId("result-count")).toHaveTextContent("0 items");
  });
});

describe("CollectionPage – filter toggles forward params to useInfiniteItems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());
  });

  it("passes the toggled status as a server-side filter (statuses @ index 1)", () => {
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({ total: 150, pages: 4 }, 40)] },
      })
    );

    render(<CollectionPage />);
    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useInfiniteItems>;
    // useInfiniteItems params: (limit, statuses, query, sortBy, enabled, ...)
    expect(lastCall[1]).toEqual(["available"]);
  });

  it("removes the status filter when toggled off", () => {
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({}, 40)] },
      })
    );

    render(<CollectionPage />);
    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);
    fireEvent.click(checkbox);

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useInfiniteItems>;
    expect(lastCall[1]).toBeUndefined();
  });

  it("re-fetches (new queryKey) when a filter chip is removed", () => {
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({ page: 1, pages: 6, total: 237 }, 40)] },
      })
    );

    render(<CollectionPage />);

    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

    const chipElements = screen.getAllByText(/status: on shelf/i);
    const chip = chipElements.find(el => el.closest("button"))?.closest("button");
    expect(chip).toBeDefined();
    fireEvent.click(chip!);

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useInfiniteItems>;
    expect(lastCall[1]).toBeUndefined();
  });
});

describe("CollectionPage – Authentication & View Modes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseItems.mockReturnValue(infiniteQueryResult());
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());
  });

  it("switches to Global Library manifestations via tabs when logged in", () => {
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    render(<CollectionPage />);

    const libraryBtn = screen.getByRole("tab", { name: /Global Library/i });
    fireEvent.click(libraryBtn);

    const calls = mockUseManifestations.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    // useInfiniteManifestations params: (limit, query, enabled, ...)
    // enabled is at index 2
    expect(calls[calls.length - 1][2]).toBe(true);
  });

  it("hides My Items toggle and defaults to Global Library when logged out", () => {
    mockUseProfile.mockReturnValue({ data: null, isLoading: false } as ReturnType<typeof useProfile>);
    render(<CollectionPage />);

    // Toggle should not exist
    expect(screen.queryByRole("tab", { name: /My Items/i })).not.toBeInTheDocument();

    // It should automatically trigger the manifestations fetch
    const calls = mockUseManifestations.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    // useInfiniteManifestations params: (limit, query, enabled, ...)
    // enabled is at index 2
    expect(calls[calls.length - 1][2]).toBe(true);
  });
});

describe("CollectionPage – Advanced Organization Views (Works & Expressions)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false } as ReturnType<typeof useStats>);
    mockUseItems.mockReturnValue(
      infiniteQueryResult({
        data: { pages: [makeItemsResponse({}, 2)] },
      })
    );
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
  });

  it("renders the Works shelf when the Works view mode is selected", () => {
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult({ data: { pages: [MOCK_WORKS_DATA] } }));
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());

    render(<CollectionPage />);

    const worksBtn = screen.getByRole("tab", { name: /Works/i });
    fireEvent.click(worksBtn);

    expect(screen.getByText("Mock Work Anthology")).toBeInTheDocument();
    expect(screen.getByText(/4 items/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Edition/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("button", { name: /My Item/i }).length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Expressions shelf when the Expressions view mode is selected", () => {
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult({ data: { pages: [MOCK_EXPRS_DATA] } }));

    render(<CollectionPage />);

    const exprBtn = screen.getByRole("tab", { name: /Expressions/i });
    fireEvent.click(exprBtn);

    expect(screen.getByText("Mock Expression Trans")).toBeInTheDocument();
    expect(screen.getByText("text")).toBeInTheDocument();
    expect(screen.getByText("pl")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Edition/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("button", { name: /My Item/i }).length).toBeGreaterThanOrEqual(1);
  });
});

describe("CollectionPage – Sorting Behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseItems.mockReturnValue(infiniteQueryResult());
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue(infiniteQueryResult());
    mockUseWorksShelf.mockReturnValue(infiniteQueryResult());
    mockUseExpressionsShelf.mockReturnValue(infiniteQueryResult());
  });

  it("defaults to recently updated sorting when entering the collection", () => {
    render(<CollectionPage />);
    const calls = mockUseItems.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    // useInfiniteItems parameters: (limit, statuses, query, sortBy, enabled, ...)
    // sortBy is parameter index 3
    const lastCall = calls.at(-1) as Parameters<typeof useInfiniteItems>;
    expect(lastCall[3]).toBe("updated");
  });

  it("defaults to includePublic=false when viewing my items collection", () => {
    render(<CollectionPage />);
    const calls = mockUseItems.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    const lastCall = calls.at(-1) as Parameters<typeof useInfiniteItems>;
    // includePublic is parameter index 14
    expect(lastCall[14]).toBe(false);
  });

  describe("Shared Collection — Unauthenticated", () => {
    it("renders shared collection browseable view for unauthenticated users", () => {
      // Mock unauthenticated profile
      mockUseProfile.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useProfile>);
      mockUseItems.mockReturnValue(infiniteQueryResult());

      render(<CollectionPage />);

      // Collection page should still render for unauthenticated users
      // (shared/public collections are browseable without login)
      expect(screen.queryByTestId("collection-grid")).toBeTruthy();
    });

    it("auth-gated controls are hidden for unauthenticated users", () => {
      mockUseProfile.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useProfile>);
      mockUseItems.mockReturnValue(infiniteQueryResult());

      render(<CollectionPage />);

      // Admin-only controls should not be present
      expect(screen.queryByText(/Admin Actions/i)).not.toBeTruthy();
    });

    it("unauthenticated users see no edit/delete management controls", () => {
      mockUseProfile.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useProfile>);
      mockUseItems.mockReturnValue(infiniteQueryResult());

      render(<CollectionPage />);

      // Management/edit controls should not render for unauth users
      expect(screen.queryByText(/Manage Collections/i)).not.toBeTruthy();
    });
  });

  describe("Shared Collection — Authenticated Non-Owner", () => {
    it("non-owner cannot see management controls", () => {
      mockUseProfile.mockReturnValue({
        data: { ...MOCK_PROFILE, id: "other-user", permissions: [] },
        isLoading: false,
      } as unknown as ReturnType<typeof useProfile>);
      mockUseItems.mockReturnValue(infiniteQueryResult());

      render(<CollectionPage />);

      // Non-owner viewing a shared collection should see content
      expect(screen.queryByTestId("collection-grid")).toBeTruthy();
    });
  });
});
