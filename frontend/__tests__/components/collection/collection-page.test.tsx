/**
 * Tests for the CollectionPage component.
 *
 * Focuses on the three behavioral fixes made in the pagination/filtering
 * overhaul:
 *
 *  1. statusCounts shown in the sidebar come from useStats() (global totals)
 *     and are therefore accurate across all pages, not just the visible 40.
 *  2. resultCount displayed in the FilterBar is meta.total from the API
 *     response, not the length of the local items array.
 *  3. When a status filter is toggled, the page number resets to 1 and the
 *     selected status is forwarded to useItems() as a server-side filter.
 *
 * useItems and useStats are mocked; sub-components that don't contribute to
 * the tested behavior (Navbar, CollectionGrid, MobileFilterDrawer) are
 * stubbed to keep the test surface small and fast.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock hooks ─────────────────────────────────────────────────────────────
vi.mock("@/lib/api/hooks", () => ({
  useItems: vi.fn(),
  useStats: vi.fn(),
}));

// ── Stub heavy / irrelevant sub-components ─────────────────────────────────
vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/collection/collection-grid", () => ({
  CollectionGrid: ({ items }: { items: unknown[] }) => (
    <div data-testid="collection-grid">{items.length} rendered</div>
  ),
}));

vi.mock("@/components/collection/mobile-filter-drawer", () => ({
  MobileFilterDrawer: () => <div data-testid="mobile-filter-drawer" />,
}));

// ── Imports (after mocks are defined) ─────────────────────────────────────
import { useItems, useStats } from "@/lib/api/hooks";
import CollectionPage from "@/app/collection/page";
import type { ApiResponse, DashboardStats } from "@/types/frbr";
import type { Item } from "@/types/frbr";

const mockUseItems = vi.mocked(useItems);
const mockUseStats = vi.mocked(useStats);

// ── Fixtures ──────────────────────────────────────────────────────────────

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
  items_wish_list: 20,
  items_reading: 10,
  items_read: 50,
};

function makeItemsResponse(
  overrides: Partial<NonNullable<ApiResponse<Item[]>["meta"]>> = {},
  dataLength = 2
): ApiResponse<Item[]> {
  const items: Item[] = Array.from({ length: dataLength }, (_, i) => ({
    id: i + 1,
    manifestation_id: i + 1,
    owner_id: "user1",
    status: "available" as const,
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
    // Only 2 items loaded on this page (both "available"), but the library
    // actually contains many more across all statuses.
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({}, 2),
      isLoading: false,
    } as ReturnType<typeof useItems>);
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
  });

  it("shows the global 'available' count from useStats, not the page count", () => {
    render(<CollectionPage />);
    // FULL_STATS.items_available = 150. The page only loaded 2 "available" items.
    // The sidebar count must reflect 150, not 2.
    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("shows the global 'lent' count from useStats", () => {
    render(<CollectionPage />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows the global 'wish_list' count from useStats", () => {
    render(<CollectionPage />);
    expect(screen.getByText("20")).toBeInTheDocument();
  });

  it("falls back to 0 when useStats has not yet loaded", () => {
    mockUseStats.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useStats>);
    render(<CollectionPage />);
    // All status counts should show "0" while stats are loading.
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBeGreaterThan(0);
  });
});

describe("CollectionPage – resultCount from meta.total", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
  });

  it("shows meta.total as the result count, not the local items length", () => {
    // 2 items on this page, but 237 total across all pages.
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ total: 237 }, 2),
      isLoading: false,
    } as ReturnType<typeof useItems>);
    render(<CollectionPage />);
    // FilterBar renders "<total> items" – should be 237, not 2.
    expect(screen.getByText("237")).toBeInTheDocument();
  });

  it("shows 0 items while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useItems>);
    render(<CollectionPage />);
    // meta.total defaults to 0 when data is undefined.
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});

describe("CollectionPage – filter toggles reset page to 1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
  });

  it("resets to page 1 when a status filter is toggled from page 2", () => {
    // Render with 6 pages so the pagination controls appear.
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ page: 1, pages: 6, total: 237 }, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);

    // Advance to page 2 via the "Next" button.
    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    // The internal page state is now 2; useItems was just called with page=2.
    const afterNextCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(afterNextCall[0]).toBe(2);

    // Toggle the "On Shelf" status filter.
    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

    // The page must have been reset to 1 after the filter toggle.
    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[0]).toBe(1);
  });

  it("passes the toggled status to useItems as a server-side filter", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ total: 150, pages: 4 }, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);

    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

    // After toggling, useItems should have been called with statuses=["available"].
    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[2]).toEqual(["available"]); // statuses argument
  });

  it("removes the status filter from useItems when toggled off", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({}, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);

    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    // Toggle on, then off.
    fireEvent.click(checkbox);
    fireEvent.click(checkbox);

    // After toggling off, statuses should be undefined (no filter).
    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[2]).toBeUndefined();
  });

  it("resets page to 1 when the active filter chip is removed", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ page: 1, pages: 6, total: 237 }, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);

    // Activate a filter, advance a page, then remove the chip.
    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox); // toggles filter on, resets to page 1

    // Advance to page 2.
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    const afterNextCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(afterNextCall[0]).toBe(2);

    // Remove the filter chip from the FilterBar.
    const chip = screen.getByText(/status: on shelf/i).closest("button");
    expect(chip).not.toBeNull();
    fireEvent.click(chip!);

    // Page should be reset to 1 and statuses filter cleared.
    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[0]).toBe(1);
    expect(lastCall[2]).toBeUndefined();
  });
});
