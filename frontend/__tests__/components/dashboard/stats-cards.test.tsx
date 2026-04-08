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
 * Tests for the StatsCards component.
 *
 * useStats is mocked so we can control loading, error, and data states
 * without running real HTTP requests.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/hooks", () => ({
  useStats: vi.fn(),
  useManifestations: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
}));

import { useStats } from "@/lib/api/hooks";
import { StatsCards } from "@/components/dashboard/stats-cards";

const mockUseStats = vi.mocked(useStats);

const FULL_STATS = {
  total_items: 42,
  lent_items: 3,
  to_read: 10,
  items_reading: 5,
  works: 30,
  expressions: 31,
  manifestations: 40,
  items: 42,
  items_available: 29,
  items_lent: 3,
  items_lost: 0,
  items_wish_list: 10,
  items_read: 0,
};

describe("StatsCards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders four stat card labels", () => {
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    expect(screen.getByText("Items")).toBeInTheDocument();
    expect(screen.getByText("Lent Out")).toBeInTheDocument();
    expect(screen.getByText("On Wish List")).toBeInTheDocument();
    expect(screen.getByText("Reading")).toBeInTheDocument();
  });

  it("displays numeric values when data is loaded", () => {
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("does not show numeric values while loading", () => {
    mockUseStats.mockReturnValue({ data: undefined, isLoading: true, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    expect(screen.queryByText("42")).not.toBeInTheDocument();
    expect(screen.queryByText("3")).not.toBeInTheDocument();
    expect(screen.queryByText("10")).not.toBeInTheDocument();
    expect(screen.queryByText("5")).not.toBeInTheDocument();
  });

  it("shows em-dash placeholders when the API returns an error", () => {
    mockUseStats.mockReturnValue({ data: undefined, isLoading: false, isError: true } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    const dashes = screen.getAllByText("—");
    // One dash per stat card
    expect(dashes).toHaveLength(4);
  });

  it("is wrapped in a landmark section for accessibility", () => {
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    expect(screen.getByRole("region", { name: /collection statistics/i })).toBeInTheDocument();
  });

  it("shows descriptive subtitles below each value", () => {
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    expect(screen.getByText("Total in collection")).toBeInTheDocument();
    expect(screen.getByText("Currently with friends")).toBeInTheDocument();
    expect(screen.getByText("On your list")).toBeInTheDocument();
    expect(screen.getByText("Currently active reads")).toBeInTheDocument();
  });

  it("renders links with the correct URLs for filtering collections", () => {
    mockUseStats.mockReturnValue({ data: FULL_STATS, isLoading: false, isError: false } as ReturnType<typeof useStats>);
    render(<StatsCards />);
    
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(4);
    
    expect(links[0]).toHaveAttribute("href", "/collection");
    expect(links[1]).toHaveAttribute("href", "/collection?statuses=reading");
    expect(links[2]).toHaveAttribute("href", "/collection?statuses=wish_list");
    expect(links[3]).toHaveAttribute("href", "/collection?statuses=lent");
  });
});
