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
});
