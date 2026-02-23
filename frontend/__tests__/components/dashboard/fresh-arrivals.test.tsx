/**
 * Tests for the FreshArrivals component.
 *
 * useItems is mocked so we can simulate loading, error, and data states.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useItems: vi.fn(),
}));

import { useItems } from "@/lib/api/hooks";
import { FreshArrivals } from "@/components/dashboard/fresh-arrivals";

const mockUseItems = vi.mocked(useItems);

function makeApiResponse(items: Item[]) {
  return {
    data: { success: true, data: items, error: null, meta: { page: 1, limit: 12, total: items.length, pages: 1 } },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useItems>;
}

const SAMPLE_ITEMS: Item[] = [
  { id: 1, manifestation_id: 1, owner_id: "u1", status: "available", meta: {}, title: "Dune", authors: ["Frank Herbert"] },
  { id: 2, manifestation_id: 2, owner_id: "u1", status: "available", meta: {}, title: "Recursion", authors: ["Blake Crouch"] },
];

describe("FreshArrivals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the section heading", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<FreshArrivals />);
    expect(screen.getByText("Fresh Arrivals")).toBeInTheDocument();
  });

  it("renders a 'View all' link pointing to /collection", () => {
    mockUseItems.mockReturnValue(makeApiResponse(SAMPLE_ITEMS));
    render(<FreshArrivals />);
    const link = screen.getByRole("link", { name: /view all/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("does not show item titles while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useItems>);
    render(<FreshArrivals />);
    expect(screen.queryByText("Dune")).not.toBeInTheDocument();
  });

  it("shows item titles when data is loaded", () => {
    mockUseItems.mockReturnValue(makeApiResponse(SAMPLE_ITEMS));
    render(<FreshArrivals />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
    expect(screen.getByText("Recursion")).toBeInTheDocument();
  });

  it("shows an error message when the API fails", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useItems>);
    render(<FreshArrivals />);
    expect(screen.getByText(/api may be unavailable/i)).toBeInTheDocument();
  });

  it("renders item links pointing to the correct item detail page", () => {
    mockUseItems.mockReturnValue(makeApiResponse(SAMPLE_ITEMS));
    render(<FreshArrivals />);
    const links = screen.getAllByRole("link", { name: /dune/i });
    expect(links[0]).toHaveAttribute("href", "/item/1");
  });

  it("is wrapped in a landmark section for accessibility", () => {
    mockUseItems.mockReturnValue(makeApiResponse(SAMPLE_ITEMS));
    render(<FreshArrivals />);
    expect(screen.getByRole("region", { name: /recently added items/i })).toBeInTheDocument();
  });
});
