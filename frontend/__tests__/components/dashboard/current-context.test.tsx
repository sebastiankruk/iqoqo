/**
 * Tests for the CurrentContext component.
 *
 * useItems is mocked to test loading, empty, and populated wish-list states.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useItems: vi.fn(),
}));

import { useItems } from "@/lib/api/hooks";
import { CurrentContext } from "@/components/dashboard/current-context";

const mockUseItems = vi.mocked(useItems);

function makeApiResponse(items: Item[]) {
  return {
    data: { success: true, data: items, error: null, meta: { page: 1, limit: 10, total: items.length, pages: 1 } },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useItems>;
}

const WISH_LIST_ITEM: Item = {
  id: 5,
  manifestation_id: 5,
  owner_id: "u1",
  status: "wish_list",
  meta: {},
  title: "Project Hail Mary",
  authors: ["Andy Weir"],
};

const AVAILABLE_ITEM: Item = {
  id: 6,
  manifestation_id: 6,
  owner_id: "u1",
  status: "available",
  meta: {},
  title: "The Martian",
  authors: ["Andy Weir"],
};

describe("CurrentContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 'To Read' heading", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    expect(screen.getByText("To Read")).toBeInTheDocument();
  });

  it("is wrapped in a landmark section for accessibility", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently active items/i })).toBeInTheDocument();
  });

  it("shows an empty state message when there are no wish_list items", () => {
    mockUseItems.mockReturnValue(makeApiResponse([AVAILABLE_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByText(/to read.*list is empty/i)).toBeInTheDocument();
  });

  it("renders a link to /collection from the empty state", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    const link = screen.getByRole("link", { name: /browse your collection/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("does not show item titles while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useItems>);
    render(<CurrentContext />);
    expect(screen.queryByText("Project Hail Mary")).not.toBeInTheDocument();
  });

  it("displays wish_list items when present", () => {
    mockUseItems.mockReturnValue(
      makeApiResponse([WISH_LIST_ITEM, AVAILABLE_ITEM]),
    );
    render(<CurrentContext />);
    expect(screen.getByText("Project Hail Mary")).toBeInTheDocument();
  });

  it("filters out non-wish_list items", () => {
    mockUseItems.mockReturnValue(
      makeApiResponse([WISH_LIST_ITEM, AVAILABLE_ITEM]),
    );
    render(<CurrentContext />);
    expect(screen.queryByText("The Martian")).not.toBeInTheDocument();
  });
});
