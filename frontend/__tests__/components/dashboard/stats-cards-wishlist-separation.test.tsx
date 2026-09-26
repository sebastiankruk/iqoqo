// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
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
 * Dashboard stats tests for the wishlist-api-separation change.
 *
 * Covers wishlist-api-separation Task 5.3:
 *   - Dashboard stats cards clearly distinguish between physical inventory count
 *     and wishlist intent count.
 *
 * These tests verify that the StatsCards component:
 *   1. Renders "My Items" (physical inventory) and "On Wish List" as separate cards
 *   2. Uses distinct data fields for each count
 *   3. Does not conflate physical items with wishlist entries
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/hooks", () => ({
  useStats: vi.fn(),
  useManifestations: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
  useVelocityInsights: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
  useDistributionInsights: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
}));

vi.mock("@/components/dashboard/collection-insights", () => ({
  CollectionInsights: ({ scope }: { scope?: string }) => (
    <div data-testid="mock-collection-insights" data-scope={scope}>
      Collection Insights Mock
    </div>
  ),
}));

import { useStats } from "@/lib/api/hooks";
import { StatsCards } from "@/components/dashboard/stats-cards";

const mockUseStats = vi.mocked(useStats);

/**
 * Mock stats payload with SEPARATE fields for physical inventory and wishlist.
 * After the wishlist-api-separation change, these should be distinct counts.
 */
const SEPARATED_STATS = {
  // Physical inventory counts
  total_items: 42,
  items: 42,
  items_available: 29,
  items_lent: 3,
  items_lost: 0,
  items_reading_count: 5,
  items_read: 0,

  // Wishlist counts (separate from physical)
  items_wish_list: 10,
  to_read: 10,

  // Other
  lent_items: 3,
  borrowed_items: 2,
  works: 30,
  expressions: 31,
  manifestations: 40,
};

describe("StatsCards — Physical vs Wishlist separation (Task 5.3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'My Items' card with physical inventory count (not including wishlist)", () => {
    mockUseStats.mockReturnValue({
      data: SEPARATED_STATS,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>);

    render(<StatsCards />);

    // "My Items" should show physical inventory count (42), NOT including wishlist
    const myItemsLabel = screen.getByText("My Items");
    expect(myItemsLabel).toBeInTheDocument();

    // The physical items count should be displayed
    // (42 total physical items, separate from 10 wishlist items)
    const physicalCount = screen.getByText("42");
    expect(physicalCount).toBeInTheDocument();
  });

  it("renders 'On Wish List' card with wishlist-only count", () => {
    mockUseStats.mockReturnValue({
      data: SEPARATED_STATS,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>);

    render(<StatsCards />);

    // "On Wish List" should show wishlist count (10), separate from physical
    const wishListLabel = screen.getByText("On Wish List");
    expect(wishListLabel).toBeInTheDocument();

    // The wishlist count should be displayed
    const wishListCount = screen.getByText("10");
    expect(wishListCount).toBeInTheDocument();
  });

  it("physical items count does NOT include wishlist entries", () => {
    const statsWithoutWishlist = {
      ...SEPARATED_STATS,
      items_wish_list: 0,
      to_read: 0,
    };

    mockUseStats.mockReturnValue({
      data: statsWithoutWishlist,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>);

    render(<StatsCards />);

    // Physical items count should remain 42 regardless of wishlist count
    const physicalCount = screen.getByText("42");
    expect(physicalCount).toBeInTheDocument();
  });

  it("wishlist count is independent of physical inventory count", () => {
    const statsWithHighWishlist = {
      ...SEPARATED_STATS,
      items_wish_list: 100,
      to_read: 100,
      total_items: 5,
      items: 5,
    };

    mockUseStats.mockReturnValue({
      data: statsWithHighWishlist,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>);

    render(<StatsCards />);

    // Both labels should still be present
    expect(screen.getByText("My Items")).toBeInTheDocument();
    expect(screen.getByText("On Wish List")).toBeInTheDocument();

    // Wishlist should show 100
    const wishListCount = screen.getByText("100");
    expect(wishListCount).toBeInTheDocument();

    // Physical should show 5
    const physicalCount = screen.getByText("5");
    expect(physicalCount).toBeInTheDocument();
  });

  it("does not conflate physical and wishlist in loading state", () => {
    mockUseStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useStats>);

    render(<StatsCards />);

    // Should not crash or show NaN/undefined
    // The component should handle loading gracefully
    expect(screen.queryByText("NaN")).not.toBeInTheDocument();
    expect(screen.queryByText("undefined")).not.toBeInTheDocument();
  });
});
