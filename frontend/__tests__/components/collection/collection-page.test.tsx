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
 * overhaul:
 *
 * 1. statusCounts shown in the sidebar come from useStats() (global totals)
 * and are therefore accurate across all pages, not just the visible 40.
 * 2. resultCount displayed in the FilterBar is meta.total from the API
 * response, not the length of the local items array.
 * 3. When a status filter is toggled, the page number resets to 1 and the
 * selected status is forwarded to useItems() as a server-side filter.
 *
 * useItems and useStats are mocked; sub-components that don't contribute to
 * the tested behavior (Navbar, CollectionGrid, MobileFilterDrawer) are
 * stubbed to keep the test surface small and fast.
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
 * Focuses on the three behavioral fixes made in the pagination/filtering
 * overhaul:
 *
 * 1. statusCounts shown in the sidebar come from useStats() (global totals)
 * and are therefore accurate across all pages, not just the visible 40.
 * 2. resultCount displayed in the FilterBar is meta.total from the API
 * response, not the length of the local items array.
 * 3. When a status filter is toggled, the page number resets to 1 and the
 * selected status is forwarded to useItems() as a server-side filter.
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
  useProfile: vi.fn(),
  useManifestations: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
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
  CollectionGrid: ({ items }: { items: unknown[] }) => (
    <div data-testid="collection-grid">{items.length} rendered</div>
  ),
}));

vi.mock("@/components/collection/mobile-filter-drawer", () => ({
  /**
   * Test stub: MobileFilterDrawer component.
   * @returns {JSX.Element}
   */
  MobileFilterDrawer: () => <div data-testid="mobile-filter-drawer" />,
}));

// ── Imports (after mocks are defined) ─────────────────────────────────────
import { useItems, useStats, useManifestations, useProfile } from "@/lib/api/hooks";
import CollectionPage from "@/app/collection/page";
import type { ApiResponse, DashboardStats, UserProfile, Item } from "@/types/frbr";

const mockUseItems = vi.mocked(useItems);
const mockUseStats = vi.mocked(useStats);
const mockUseManifestations = vi.mocked(useManifestations);
const mockUseProfile = vi.mocked(useProfile);

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
  items_wish_list: 20,
  items_reading: 10,
  items_read: 50,
  items_unread: 20,
};

/** Mock user profile */
const MOCK_PROFILE: UserProfile = { id: "1", email: "test@example.com" };

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
    // Simulate a logged-in user so the page renders normally
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({}, 2),
      isLoading: false,
    } as ReturnType<typeof useItems>);
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useManifestations>);
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
    expect(screen.getByText("20")).toBeInTheDocument();
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
    mockUseManifestations.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useManifestations>);
  });

  it("shows meta.total as the result count, not the local items length", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ total: 237 }, 2),
      isLoading: false,
    } as ReturnType<typeof useItems>);
    render(<CollectionPage />);
    expect(screen.getByText("237")).toBeInTheDocument();
  });

  it("shows 0 items while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useItems>);
    render(<CollectionPage />);
    expect(screen.getByText(/0 items/i)).toBeInTheDocument();
  });
});

describe("CollectionPage – filter toggles reset page to 1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    mockUseStats.mockReturnValue({
      data: FULL_STATS,
      isLoading: false,
    } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useManifestations>);
  });

  it("resets to page 1 when a status filter is toggled from page 2", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ page: 1, pages: 6, total: 237 }, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);
    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    const afterNextCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(afterNextCall[0]).toBe(2);

    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

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

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[2]).toEqual(["available"]);
  });

  it("removes the status filter from useItems when toggled off", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({}, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);
    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);
    fireEvent.click(checkbox);

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[2]).toBeUndefined();
  });

  it("resets page to 1 when the active filter chip is removed", () => {
    mockUseItems.mockReturnValue({
      data: makeItemsResponse({ page: 1, pages: 6, total: 237 }, 40),
      isLoading: false,
    } as ReturnType<typeof useItems>);

    render(<CollectionPage />);

    const checkbox = screen.getByRole("checkbox", { name: /on shelf/i });
    fireEvent.click(checkbox);

    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    const afterNextCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(afterNextCall[0]).toBe(2);

    const chip = screen.getByText(/status: on shelf/i).closest("button");
    expect(chip).not.toBeNull();
    fireEvent.click(chip!);

    const lastCall = mockUseItems.mock.calls.at(-1) as Parameters<typeof useItems>;
    expect(lastCall[0]).toBe(1);
    expect(lastCall[2]).toBeUndefined();
  });
});

describe("CollectionPage – Authentication & View Modes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseItems.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useItems>);
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false } as ReturnType<typeof useStats>);
    mockUseManifestations.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useManifestations>);
  });

  it("switches to Global Library manifestations via tabs when logged in", () => {
    mockUseProfile.mockReturnValue({ data: MOCK_PROFILE, isLoading: false } as ReturnType<typeof useProfile>);
    render(<CollectionPage />);

    const libraryBtn = screen.getByRole("button", { name: /Global Library/i });
    fireEvent.click(libraryBtn);

    const calls = mockUseManifestations.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    // Index [3] is the `enabled` parameter (page, limit, query, enabled)
    expect(calls[calls.length - 1][3]).toBe(true);
  });

  it("hides My Items toggle and defaults to Global Library when logged out", () => {
    mockUseProfile.mockReturnValue({ data: null, isLoading: false } as ReturnType<typeof useProfile>);
    render(<CollectionPage />);

    // Toggle should not exist
    expect(screen.queryByRole("button", { name: /My Items/i })).not.toBeInTheDocument();

    // It should automatically trigger the manifestations fetch
    const calls = mockUseManifestations.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    // Index [3] is the `enabled` parameter (page, limit, query, enabled)
    expect(calls[calls.length - 1][3]).toBe(true);
  });
});
